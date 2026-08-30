"""Wellfile document extraction ADK tools.

Checks BigQuery cache first, then falls back to reading the wellfile PDF from GCS
and extracting data via Gemini 2.5 Flash Lite Structured Outputs.

Now supports four focused extraction categories:
  - Priority 1: Completion / Stimulation / Tubulars
  - Priority 2: Geology (formation tops, hydrocarbon shows)
  - Priority 3: Casing / Cement / Zonal Isolation
  - Priority 4: Drilling (mud, bits, wellbore events)
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
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from mt_oil.agents.telemetry import Timer, emit_agent_telemetry
from mt_oil.config import settings
from mt_oil.schemas.wellfile import (
    CompletionStimulationData,
    GeologyData,
    CasingCementData,
    DrillingData,
    DiagnosticData,
    WaterAnalysis,
    FluidPvt,
    FlowbackData,
    DirectionalSurvey,
)

logger = logging.getLogger(__name__)

PDF_PREFIX = "wells/pdfs/"

# ---- helpers -----------------------------------------------------------------


def _get_api_10(api_number: str) -> str:
    return api_number.strip()[:10]


def _gcs_blob_name(api_number: str) -> str:
    api_10 = _get_api_10(api_number)
    return f"{PDF_PREFIX}{api_number}/{api_10}.pdf"


def _gcs_uri(api_number: str) -> str:
    return f"gs://{settings.gcs_data_bucket}/{_gcs_blob_name(api_number)}"


def _bq_table() -> str:
    return f"`{settings.gcp_project_id}.{settings.bigquery_dataset}.{settings.wellfile_parsed_table}`"


# ---- PDF download helpers ----------------------------------------------------

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
    "image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Referer": "https://bogfiles.dnrc.mt.gov/",
}


def _state_pdf_url(api_number: str) -> str | None:
    api_10 = api_number.strip()[:10]
    if len(api_10) < 10:
        return None
    return f"https://bogfiles.dnrc.mt.gov/Well_Data/{api_10}/{api_10}.pdf"


def _download_pdf_bytes(api_number: str) -> bytes | None:
    """Download a wellfile PDF from the state DNRC server."""
    url = _state_pdf_url(api_number)
    if url is None:
        return None
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    req = Request(url, headers=BROWSER_HEADERS)
    try:
        with urlopen(req, timeout=60) as resp:
            ct = (resp.headers.get("Content-Type") or "").lower()
            if "application/pdf" not in ct:
                logger.warning(
                    "State PDF for %s: Content-Type=%s (not PDF)", api_number, ct
                )
                return None
            data = resp.read()
            if not data:
                logger.warning("State PDF for %s: empty response", api_number)
                return None
            return data
    except HTTPError as e:
        if e.code == 404:
            logger.warning("State PDF not found (404) for %s", api_number)
        else:
            logger.warning("State download failed for %s: HTTP %s", api_number, e.code)
        return None
    except (URLError, OSError) as e:
        logger.warning("State download failed for %s: %s", api_number, e)
        return None


def _cache_pdf_to_gcs(api_number: str, pdf_bytes: bytes) -> None:
    """Upload a PDF to GCS so it's available for future requests."""
    if not settings.gcp_project_id or not settings.gcs_data_bucket:
        return
    try:
        client = storage.Client(project=settings.gcp_project_id or None)
        bucket = client.bucket(settings.gcs_data_bucket)
        blob = bucket.blob(_gcs_blob_name(api_number))
        blob.upload_from_string(pdf_bytes, content_type="application/pdf")
        logger.info("Cached state PDF to GCS for %s", api_number)
    except Exception as exc:
        logger.warning("Failed to cache PDF to GCS for %s: %s", api_number, exc)


def _read_pdf(api_number: str) -> Optional[bytes]:
    """Download the wellfile PDF from GCS, falling back to the state DNRC server."""
    client = storage.Client(project=settings.gcp_project_id or None)
    bucket = client.bucket(settings.gcs_data_bucket)
    blob = bucket.blob(_gcs_blob_name(api_number))
    if blob.exists():
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        blob.download_to_file(tmp)
        tmp.close()
        with open(tmp.name, "rb") as f:
            data = f.read()
        Path(tmp.name).unlink(missing_ok=True)
        return data

    logger.warning("PDF not found in GCS for %s, attempting state download", api_number)
    pdf_bytes = _download_pdf_bytes(api_number)
    if pdf_bytes is not None:
        _cache_pdf_to_gcs(api_number, pdf_bytes)
    return pdf_bytes


# Alias for the batch extraction job that imports this name.
_read_pdf_from_gcs = _read_pdf


# ---- BigQuery payload cache -------------------------------------------------


def _read_payload_from_bq(api_number: str) -> Optional[dict]:
    """Read the full payload JSON from the BigQuery cache."""
    if not settings.gcp_project_id or not settings.bigquery_dataset:
        return None
    try:
        client = bigquery.Client(project=settings.gcp_project_id)
        query = f"""
            SELECT payload
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
        payload = df.iloc[0].get("payload")
        if payload is None:
            return None
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return None
        if not isinstance(payload, dict):
            return None
        return payload
    except Exception as exc:
        logger.warning("BQ payload read failed for %s: %s", api_number, exc)
        return None


def _check_bq_cache_section(api_number: str, section_name: str) -> Optional[dict]:
    """Return the cached section dict or None."""
    payload = _read_payload_from_bq(api_number)
    if payload is None:
        return None
    if not isinstance(payload, dict):
        return None
    section = payload.get(section_name)
    if section is None:
        return None
    return section


def _write_section_to_bq(
    api_number: str,
    section_name: str,
    section_data: dict,
    gcs_uri: str,
    timer: Timer,
) -> None:
    """Upsert a section into the payload JSON column in BigQuery."""
    if not settings.gcp_project_id or not settings.bigquery_dataset:
        return
    client = bigquery.Client(project=settings.gcp_project_id)
    import datetime

    existing = _read_payload_from_bq(api_number)
    full_payload = existing or {}
    full_payload[section_name] = section_data
    full_payload_json = json.dumps(full_payload)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    merge_sql = f"""
        MERGE INTO {_bq_table()} T
        USING (SELECT @api_number AS api_number) S
        ON T.api_number = S.api_number
        WHEN MATCHED THEN UPDATE SET
            payload = PARSE_JSON(@full_payload_json),
            extraction_status = 'SUCCESS',
            extracted_at = @extracted_at
        WHEN NOT MATCHED THEN INSERT
            (api_number, payload, extraction_status, extracted_at,
             gcs_uri, input_tokens, output_tokens, latency_ms)
        VALUES
            (@api_number, PARSE_JSON(@full_payload_json),
             'SUCCESS', @extracted_at,
             @gcs_uri, @input_tokens, @output_tokens, @latency_ms)
    """
    params = [
        bigquery.ScalarQueryParameter("api_number", "STRING", api_number),
        bigquery.ScalarQueryParameter("full_payload_json", "STRING", full_payload_json),
        bigquery.ScalarQueryParameter("extracted_at", "TIMESTAMP", now),
        bigquery.ScalarQueryParameter("gcs_uri", "STRING", gcs_uri),
        bigquery.ScalarQueryParameter("input_tokens", "INT64", None),
        bigquery.ScalarQueryParameter("output_tokens", "INT64", None),
        bigquery.ScalarQueryParameter(
            "latency_ms", "FLOAT64", round(timer.elapsed_ms, 1)
        ),
    ]
    client.query(
        merge_sql, job_config=bigquery.QueryJobConfig(query_parameters=params)
    ).result()


# ---- Legacy flat-column cache (for backward compat with old rows) -----------


def pd_notnull(val) -> bool:
    try:
        import pandas as pd

        return pd.notna(val) and val is not None
    except Exception:
        return val is not None


def _check_bq_cache(api_number: str) -> Optional[dict]:
    """Legacy: check for flat-column cache (pre-payload rows)."""
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
        logger.warning("BQ flat cache check failed for %s: %s", api_number, exc)
        return None


# ---- Gemini per-section extraction -------------------------------------------


def _extract_section(
    api_number: str,
    pdf_bytes: bytes,
    response_schema,
    prompt: str,
) -> dict:
    """Generic Gemini extraction helper.

    Uses response_mime_type="application/json" without response_schema to avoid
    Gemini INVALID_ARGUMENT errors when the Pydantic schema generates too many
    constraint states. Validation is performed client-side after extraction.
    """
    client = GenaiClient(
        project=settings.gcp_project_id,
        location=settings.vertex_ai_location,
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
        ),
    )
    text = response.text
    if not text:
        raise ValueError("Gemini returned empty response")
    data = json.loads(text)
    try:
        specs = response_schema(**data)
        return specs.model_dump(exclude_none=True)
    except ValidationError as exc:
        logger.warning(
            "Pydantic validation failed for %s: %s — returning raw JSON",
            api_number,
            exc,
        )
        return data


# -- Priority 1: Completion / Stimulation / Downhole Tubulars --

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text()


COMPLETION_PROMPT = _load_prompt("completion")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _extract_completion_with_retry(api_number: str, pdf_bytes: bytes) -> dict:
    return _extract_section(
        api_number,
        pdf_bytes,
        CompletionStimulationData,
        COMPLETION_PROMPT.format(api_number=api_number),
    )


# -- Priority 2: Geology (formation tops + hydrocarbon shows) --

GEOLOGY_PROMPT = _load_prompt("geology")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _extract_geology_with_retry(api_number: str, pdf_bytes: bytes) -> dict:
    return _extract_section(
        api_number,
        pdf_bytes,
        GeologyData,
        GEOLOGY_PROMPT.format(api_number=api_number),
    )


# -- Priority 3: Casing / Cement / Zonal Isolation --

CASING_PROMPT = _load_prompt("casing")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _extract_casing_with_retry(api_number: str, pdf_bytes: bytes) -> dict:
    return _extract_section(
        api_number,
        pdf_bytes,
        CasingCementData,
        CASING_PROMPT.format(api_number=api_number),
    )


# -- Priority 4: Drilling (mud, bits, wellbore events) --

DRILLING_PROMPT = _load_prompt("drilling")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _extract_drilling_with_retry(api_number: str, pdf_bytes: bytes) -> dict:
    return _extract_section(
        api_number,
        pdf_bytes,
        DrillingData,
        DRILLING_PROMPT.format(api_number=api_number),
    )


# -- Priority 5a: Diagnostics (DFIT / stress / step-rate) --
# Priority 5b: Water chemistry
# Priority 5c: Fluid PVT / gas composition
# Priority 5d: Flowback / load recovery
# Priority 5e: Directional survey

DIAGNOSTICS_PROMPT = _load_prompt("diagnostics")
WATER_CHEMISTRY_PROMPT = _load_prompt("water_chemistry")
FLUID_PVT_PROMPT = _load_prompt("fluid_pvt")
FLOWBACK_PROMPT = _load_prompt("flowback")
DIRECTIONAL_SURVEY_PROMPT = _load_prompt("directional_survey")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _extract_diagnostics_with_retry(api_number: str, pdf_bytes: bytes) -> dict:
    return _extract_section(
        api_number,
        pdf_bytes,
        DiagnosticData,
        DIAGNOSTICS_PROMPT.format(api_number=api_number),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _extract_water_chemistry_with_retry(api_number: str, pdf_bytes: bytes) -> dict:
    return _extract_section(
        api_number,
        pdf_bytes,
        WaterAnalysis,
        WATER_CHEMISTRY_PROMPT.format(api_number=api_number),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _extract_fluid_pvt_with_retry(api_number: str, pdf_bytes: bytes) -> dict:
    return _extract_section(
        api_number, pdf_bytes, FluidPvt, FLUID_PVT_PROMPT.format(api_number=api_number)
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _extract_flowback_with_retry(api_number: str, pdf_bytes: bytes) -> dict:
    return _extract_section(
        api_number,
        pdf_bytes,
        FlowbackData,
        FLOWBACK_PROMPT.format(api_number=api_number),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _extract_survey_with_retry(api_number: str, pdf_bytes: bytes) -> dict:
    return _extract_section(
        api_number,
        pdf_bytes,
        DirectionalSurvey,
        DIRECTIONAL_SURVEY_PROMPT.format(api_number=api_number),
    )


# ---- ADK tool functions ------------------------------------------------------


def _section_tool(api_number: str, section_name: str, extract_fn) -> dict:
    """Generic tool: check cache → extract → write → return."""
    timer = Timer()
    timer.__enter__()
    gcs_uri = _gcs_uri(api_number)

    cached = _check_bq_cache_section(api_number, section_name)
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
            section_name: cached,
        }

    pdf_bytes = None
    try:
        pdf_bytes = _read_pdf(api_number)
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
        }

    try:
        specs = extract_fn(api_number, pdf_bytes)
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
        _write_section_to_bq(api_number, section_name, specs, gcs_uri, timer)
        return {
            "extraction_status": "SUCCESS",
            "cache_hit": False,
            section_name: specs,
        }
    except Exception as exc:
        logger.error(
            "Gemini extraction failed for %s (%s): %s", api_number, section_name, exc
        )
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
        }


def wellfile_completion_tool(api_number: str) -> dict:
    """Extract completion / stimulation / downhole tubular parameters from a wellfile PDF."""
    return _section_tool(
        api_number,
        "completion_stimulation",
        _extract_completion_with_retry,
    )


def wellfile_geology_tool(api_number: str) -> dict:
    """Extract formation tops and hydrocarbon show data from a wellfile PDF."""
    return _section_tool(
        api_number,
        "geology",
        _extract_geology_with_retry,
    )


def wellfile_casing_tool(api_number: str) -> dict:
    """Extract casing, cementing, multi-stage tooling, and cement evaluation data from a wellfile PDF."""
    return _section_tool(
        api_number,
        "casing_cement",
        _extract_casing_with_retry,
    )


def wellfile_drilling_tool(api_number: str) -> dict:
    """Extract drilling fluid, bit run, and wellbore event data from a wellfile PDF."""
    return _section_tool(
        api_number,
        "drilling",
        _extract_drilling_with_retry,
    )


def wellfile_diagnostics_tool(api_number: str) -> dict:
    """Extract diagnostic / rock mechanics data (step-rate, breakdown, closure) from a wellfile PDF."""
    return _section_tool(
        api_number,
        "diagnostics",
        _extract_diagnostics_with_retry,
    )


def wellfile_water_chemistry_tool(api_number: str) -> dict:
    """Extract produced water chemistry from a wellfile PDF."""
    return _section_tool(
        api_number,
        "water_chemistry",
        _extract_water_chemistry_with_retry,
    )


def wellfile_fluid_pvt_tool(api_number: str) -> dict:
    """Extract fluid PVT and gas composition from a wellfile PDF."""
    return _section_tool(
        api_number,
        "fluid_pvt",
        _extract_fluid_pvt_with_retry,
    )


def wellfile_flowback_tool(api_number: str) -> dict:
    """Extract flowback and load recovery data from a wellfile PDF."""
    return _section_tool(
        api_number,
        "flowback",
        _extract_flowback_with_retry,
    )


def wellfile_survey_tool(api_number: str) -> dict:
    """Extract the full directional MWD survey table (no truncation) from a wellfile PDF."""
    return _section_tool(
        api_number,
        "directional_survey",
        _extract_survey_with_retry,
    )


# Keep legacy wellfile_document_tool alias for any remaining references.
def wellfile_document_tool(api_number: str) -> dict:
    """Legacy: extract all completion parameters (flat) from a wellfile PDF."""
    return wellfile_completion_tool(api_number)


# Backward-compat aliases used by batch_wellfile_extraction.py
def _extract_with_retry(api_number: str, pdf_bytes: bytes) -> dict:
    return _extract_completion_with_retry(api_number, pdf_bytes)


def _write_to_bq(api_number: str, specs: dict, gcs_uri: str, timer: Timer) -> None:
    """Legacy: write completion extraction to the payload JSON under 'completion_stimulation'."""
    _write_section_to_bq(api_number, "completion_stimulation", specs, gcs_uri, timer)
