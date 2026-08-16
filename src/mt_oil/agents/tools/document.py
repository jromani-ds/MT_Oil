"""Wellfile document extraction ADK tool.

Checks BigQuery cache first, then falls back to reading the wellfile PDF from GCS
and extracting completion parameters via Gemini 2.5 Flash Lite Structured Outputs.
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Optional

import google.cloud.bigquery as bigquery
from google.cloud import storage
from google.genai import Client as GenaiClient
from google.genai import types as genai_types
from tenacity import retry, stop_after_attempt, wait_exponential

from mt_oil.agents.telemetry import Timer, emit_agent_telemetry
from mt_oil.config import settings
from mt_oil.schemas.wellfile import CompletionSpecs

logger = logging.getLogger(__name__)

PDF_PREFIX = "wells/pdfs/"


def _get_api_10(api_number: str) -> str:
    return api_number.strip()[:10]


def _gcs_blob_name(api_number: str) -> str:
    api_10 = _get_api_10(api_number)
    return f"{PDF_PREFIX}{api_number}/{api_10}.pdf"


def _gcs_uri(api_number: str) -> str:
    return f"gs://{settings.gcs_data_bucket}/{_gcs_blob_name(api_number)}"


def _bq_table() -> str:
    return f"`{settings.gcp_project_id}.{settings.bigquery_dataset}.{settings.wellfile_parsed_table}`"


def _check_bq_cache(api_number: str) -> Optional[dict]:
    """Check if a valid extraction already exists in BigQuery."""
    if not settings.gcp_project_id or not settings.bigquery_dataset:
        return None
    try:
        client = bigquery.Client(project=settings.gcp_project_id)
        query = f"""
            SELECT *
            FROM {_bq_table()}
            WHERE api_number = @api_number
            AND extraction_status = 'SUCCESS'
            ORDER BY extracted_at DESC
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("api_number", "STRING", api_number)
            ]
        )
        df = client.query(query, job_config=job_config).to_dataframe(
            create_bqstorage_client=False
        )
        if df.empty:
            return None

        row = df.iloc[0]
        return {
            "api_number": row["api_number"],
            "well_name": row.get("well_name"),
            "tvd_ft": float(row["tvd_ft"]) if pd_notnull(row.get("tvd_ft")) else None,
            "md_ft": float(row["md_ft"]) if pd_notnull(row.get("md_ft")) else None,
            "lateral_length_ft": (
                float(row["lateral_length_ft"])
                if pd_notnull(row.get("lateral_length_ft"))
                else None
            ),
            "total_clean_fluid_bbls": (
                float(row["total_clean_fluid_bbls"])
                if pd_notnull(row.get("total_clean_fluid_bbls"))
                else None
            ),
            "total_proppant_lbs": (
                float(row["total_proppant_lbs"])
                if pd_notnull(row.get("total_proppant_lbs"))
                else None
            ),
            "max_treating_pressure_psi": (
                float(row["max_treating_pressure_psi"])
                if pd_notnull(row.get("max_treating_pressure_psi"))
                else None
            ),
            "casing_intermediate_depth_ft": (
                float(row["casing_intermediate_depth_ft"])
                if pd_notnull(row.get("casing_intermediate_depth_ft"))
                else None
            ),
            "extraction_status": "SUCCESS",
        }
    except Exception as exc:
        logger.warning("BQ cache check failed for %s: %s", api_number, exc)
        return None


def pd_notnull(val) -> bool:
    try:
        import pandas as pd

        return pd.notna(val) and val is not None
    except Exception:
        return val is not None


def _read_pdf_from_gcs(api_number: str) -> Optional[bytes]:
    """Download the wellfile PDF from GCS and return raw bytes."""
    client = storage.Client(project=settings.gcp_project_id or None)
    bucket = client.bucket(settings.gcs_data_bucket)
    blob = bucket.blob(_gcs_blob_name(api_number))
    if not blob.exists():
        logger.warning("PDF not found in GCS for %s", api_number)
        return None
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    blob.download_to_file(tmp)
    tmp.close()
    with open(tmp.name, "rb") as f:
        data = f.read()
    Path(tmp.name).unlink(missing_ok=True)
    return data


def _extract_with_gemini(api_number: str, pdf_bytes: bytes) -> dict:
    """Call Gemini 2.5 Flash Lite with Structured Outputs to extract completion specs."""
    client = GenaiClient(
        project=settings.gcp_project_id,
        location=settings.vertex_ai_location,
    )
    prompt = (
        "Extract the following completion parameters from this wellfile PDF. "
        "Return ONLY a JSON object matching the provided schema. "
        "If a value is not found or illegible, set it to null.\n\n"
        f"API Number: {api_number}\n\n"
        "Fields to extract:\n"
        "- well_name: Official well name and number\n"
        "- tvd_ft: True Vertical Depth in feet\n"
        "- md_ft: Total Measured Depth in feet\n"
        "- lateral_length_ft: Horizontal lateral length in feet\n"
        "- total_clean_fluid_bbls: Total clean fracturing fluid in barrels\n"
        "- total_proppant_lbs: Total proppant/sand weight in pounds\n"
        "- max_treating_pressure_psi: Maximum treating pressure in PSI\n"
        "- casing_intermediate_depth_ft: Intermediate casing setting depth in feet"
    )
    response = client.models.generate_content(
        model=settings.vertex_ai_model,
        contents=[
            prompt,
            genai_types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        ],
        config=genai_types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=CompletionSpecs,
        ),
    )
    text = response.text
    if not text:
        raise ValueError("Gemini returned empty response")
    # Parse JSON and validate through Pydantic
    data = json.loads(text)
    specs = CompletionSpecs(**data)
    return specs.model_dump(exclude_none=True)


def _write_to_bq(
    api_number: str, specs: dict, gcs_uri: str, timer: Timer, cache_hit: bool = False
):
    """Write extraction results to the BigQuery wellfile_parsed_metadata table."""
    if not settings.gcp_project_id or not settings.bigquery_dataset:
        return
    client = bigquery.Client(project=settings.gcp_project_id)
    import datetime

    row = {
        "api_number": api_number,
        "well_name": specs.get("well_name"),
        "tvd_ft": specs.get("tvd_ft"),
        "md_ft": specs.get("md_ft"),
        "lateral_length_ft": specs.get("lateral_length_ft"),
        "total_clean_fluid_bbls": specs.get("total_clean_fluid_bbls"),
        "total_proppant_lbs": specs.get("total_proppant_lbs"),
        "max_treating_pressure_psi": specs.get("max_treating_pressure_psi"),
        "casing_intermediate_depth_ft": specs.get("casing_intermediate_depth_ft"),
        "extraction_status": specs.get("extraction_status", "SUCCESS"),
        "extracted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gcs_uri": gcs_uri,
        "input_tokens": None,
        "output_tokens": None,
        "latency_ms": round(timer.elapsed_ms, 1),
    }

    # Use MERGE for upsert
    merge_sql = f"""
        MERGE INTO {_bq_table()} T
        USING (SELECT @api_number AS api_number) S
        ON T.api_number = S.api_number
        WHEN MATCHED THEN UPDATE SET
            well_name = @well_name,
            tvd_ft = @tvd_ft,
            md_ft = @md_ft,
            lateral_length_ft = @lateral_length_ft,
            total_clean_fluid_bbls = @total_clean_fluid_bbls,
            total_proppant_lbs = @total_proppant_lbs,
            max_treating_pressure_psi = @max_treating_pressure_psi,
            casing_intermediate_depth_ft = @casing_intermediate_depth_ft,
            extraction_status = @extraction_status,
            extracted_at = @extracted_at,
            gcs_uri = @gcs_uri,
            input_tokens = @input_tokens,
            output_tokens = @output_tokens,
            latency_ms = @latency_ms
        WHEN NOT MATCHED THEN INSERT
            (api_number, well_name, tvd_ft, md_ft, lateral_length_ft,
             total_clean_fluid_bbls, total_proppant_lbs, max_treating_pressure_psi,
             casing_intermediate_depth_ft, extraction_status, extracted_at,
             gcs_uri, input_tokens, output_tokens, latency_ms)
        VALUES
            (@api_number, @well_name, @tvd_ft, @md_ft, @lateral_length_ft,
             @total_clean_fluid_bbls, @total_proppant_lbs, @max_treating_pressure_psi,
             @casing_intermediate_depth_ft, @extraction_status, @extracted_at,
             @gcs_uri, @input_tokens, @output_tokens, @latency_ms)
    """
    params = [
        bigquery.ScalarQueryParameter("api_number", "STRING", api_number),
        bigquery.ScalarQueryParameter("well_name", "STRING", row["well_name"]),
        bigquery.ScalarQueryParameter("tvd_ft", "FLOAT64", row["tvd_ft"]),
        bigquery.ScalarQueryParameter("md_ft", "FLOAT64", row["md_ft"]),
        bigquery.ScalarQueryParameter(
            "lateral_length_ft", "FLOAT64", row["lateral_length_ft"]
        ),
        bigquery.ScalarQueryParameter(
            "total_clean_fluid_bbls", "FLOAT64", row["total_clean_fluid_bbls"]
        ),
        bigquery.ScalarQueryParameter(
            "total_proppant_lbs", "FLOAT64", row["total_proppant_lbs"]
        ),
        bigquery.ScalarQueryParameter(
            "max_treating_pressure_psi", "FLOAT64", row["max_treating_pressure_psi"]
        ),
        bigquery.ScalarQueryParameter(
            "casing_intermediate_depth_ft",
            "FLOAT64",
            row["casing_intermediate_depth_ft"],
        ),
        bigquery.ScalarQueryParameter(
            "extraction_status", "STRING", row["extraction_status"]
        ),
        bigquery.ScalarQueryParameter("extracted_at", "TIMESTAMP", row["extracted_at"]),
        bigquery.ScalarQueryParameter("gcs_uri", "STRING", row["gcs_uri"]),
        bigquery.ScalarQueryParameter("input_tokens", "INT64", row["input_tokens"]),
        bigquery.ScalarQueryParameter("output_tokens", "INT64", row["output_tokens"]),
        bigquery.ScalarQueryParameter("latency_ms", "FLOAT64", row["latency_ms"]),
    ]
    client.query(
        merge_sql, job_config=bigquery.QueryJobConfig(query_parameters=params)
    ).result()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _extract_with_retry(api_number: str, pdf_bytes: bytes) -> dict:
    return _extract_with_gemini(api_number, pdf_bytes)


def wellfile_document_tool(api_number: str) -> dict:
    """Extract completion parameters from a wellfile PDF using the BigQuery cache or Gemini on GCS.

    First checks the BigQuery wellfile_parsed_metadata table for a cached result.
    If no cache hit, reads the PDF from GCS and extracts via Gemini.

    Args:
        api_number: The 10 or 14 digit API well number.

    Returns:
        A dict with 'extraction_status', 'cache_hit', and completion specs.
    """
    timer = Timer()
    timer.__enter__()

    gcs_uri = _gcs_uri(api_number)

    cached = _check_bq_cache(api_number)
    if cached is not None:
        timer.__exit__()
        emit_agent_telemetry(
            api_number=api_number,
            gcs_uri=gcs_uri,
            input_tokens=None,
            output_tokens=None,
            latency_ms=timer.elapsed_ms,
            cache_hit=True,
        )
        return {
            "extraction_status": "SUCCESS",
            "cache_hit": True,
            **cached,
        }

    pdf_bytes = None
    try:
        pdf_bytes = _read_pdf_from_gcs(api_number)
    except Exception as exc:
        logger.error("GCS read failed for %s: %s", api_number, exc)
    if pdf_bytes is None:
        timer.__exit__()
        emit_agent_telemetry(
            api_number=api_number,
            gcs_uri=gcs_uri,
            input_tokens=None,
            output_tokens=None,
            latency_ms=timer.elapsed_ms,
            cache_hit=False,
        )
        return {
            "extraction_status": "FAILED_PARSING",
            "cache_hit": False,
            "api_number": api_number,
        }

    try:
        specs = _extract_with_retry(api_number, pdf_bytes)
        specs["extraction_status"] = "SUCCESS"
        timer.__exit__()
        emit_agent_telemetry(
            api_number=api_number,
            gcs_uri=gcs_uri,
            input_tokens=None,
            output_tokens=None,
            latency_ms=timer.elapsed_ms,
            cache_hit=False,
        )
        _write_to_bq(api_number, specs, gcs_uri, timer)
        return {
            "extraction_status": "SUCCESS",
            "cache_hit": False,
            **specs,
        }
    except Exception as exc:
        logger.error("Gemini extraction failed for %s: %s", api_number, exc)
        timer.__exit__()
        emit_agent_telemetry(
            api_number=api_number,
            gcs_uri=gcs_uri,
            input_tokens=None,
            output_tokens=None,
            latency_ms=timer.elapsed_ms,
            cache_hit=False,
        )
        return {
            "extraction_status": "FAILED_PARSING",
            "cache_hit": False,
            "api_number": api_number,
        }
