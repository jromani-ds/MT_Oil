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
from tenacity import retry, stop_after_attempt, wait_exponential

from mt_oil.agents.telemetry import Timer, emit_agent_telemetry
from mt_oil.config import settings
from mt_oil.schemas.wellfile import (
    CompletionStimulationData,
    GeologyData,
    CasingCementData,
    DrillingData,
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
            payload = json.loads(payload)
        return payload
    except Exception as exc:
        logger.warning("BQ payload read failed for %s: %s", api_number, exc)
        return None


def _check_bq_cache_section(api_number: str, section_name: str) -> Optional[dict]:
    """Return the cached section dict or None."""
    payload = _read_payload_from_bq(api_number)
    if payload is None:
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
    """Generic Gemini extraction helper."""
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
            response_schema=response_schema,
        ),
    )
    text = response.text
    if not text:
        raise ValueError("Gemini returned empty response")
    data = json.loads(text)
    specs = response_schema(**data)
    return specs.model_dump(exclude_none=True)


# -- Priority 1: Completion / Stimulation / Downhole Tubulars --

COMPLETION_PROMPT = """Extract the following completion, stimulation, and downhole tubular parameters from this wellfile PDF. Return ONLY a valid JSON object matching the provided schema. If a value is not found or illegible, set it to null. Use empty arrays when no data is available.

API Number: {api_number}

GENERAL WELL DATA:
- well_name: Official well name and number
- tvd_ft: True Vertical Depth in feet
- md_ft: Total Measured Depth in feet
- lateral_length_ft: Horizontal lateral length in feet
- total_clean_fluid_bbls: Total clean fracturing fluid in barrels
- total_proppant_lbs: Total proppant/sand weight in pounds
- max_treating_pressure_psi: Maximum treating pressure in PSI
- casing_intermediate_depth_ft: Intermediate casing setting depth in feet

IP / FLOW TEST (ip_flow_test object):
- test_duration_hrs: Duration of the test in hours
- oil_rate_24hr_bbls: 24-hour equivalent oil rate in barrels
- gas_rate_24hr_mcf: 24-hour equivalent gas rate in MCF
- water_rate_24hr_bbls: 24-hour equivalent water rate in barrels
- choke_size_inches: Choke size in inches
- flowing_tubing_pressure_psi: Flowing tubing pressure in PSI
- shut_in_tubing_pressure_psi: Shut-in tubing pressure in PSI
- test_method: How the test was conducted (swab test, flowing, etc.)

PERFORATIONS (perforations array, one entry per interval):
- top_md_ft: Top measured depth of perforated interval
- bottom_md_ft: Bottom measured depth of perforated interval
- shots_per_ft: Shots per foot
- gun_charge_diameter_in: Gun or charge diameter in inches
- gun_type: Gun or charge type description
- phase_angle_deg: Phase angle in degrees
- formation_name: Name of the formation perforated
- status: Whether open, squeezed, or isolated

STIMULATION STAGES (stimulation_stages array, one entry per stage):
- treatment_type: Type of treatment (acid breakdown, matrix acid, hydraulic fracture, etc.)
- stage_number: Sequential stage number
- fluid_volume_bbls: Fluid volume pumped in barrels
- chemical_additives: Chemical additives and their concentrations
- diverter_specs: Diverter or ball sealer specifications
- max_treating_pressure_psi: Maximum treating pressure
- avg_treating_pressure_psi: Average treating pressure
- injection_rate_bpm: Injection rate in barrels per minute
- isip_psi: Instantaneous Shut-In Pressure

DOWNHOLE TUBULARS (downhole_tubulars object):
- tubing_od_in: Tubing outer diameter in inches
- tubing_weight_lbs_ft: Tubing weight in pounds per foot
- tubing_grade: Steel grade of the tubing
- thread_type: Thread / connection type
- eot_depth_ft: End of Tubing measured depth
- seating_nipple_depth_ft: Seating Nipple measured depth
- tubing_anchor_catcher_depth_ft: Tubing Anchor Catcher measured depth
- applied_pretension_lbs: Applied pretension load in pounds
"""


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

GEOLOGY_PROMPT = """Extract geological formation tops and hydrocarbon show data from this wellfile PDF. Return ONLY a valid JSON object matching the provided schema. If a value is not found, set it to null. Use empty arrays when no data is available.

API Number: {api_number}

FORMATION TOPS (formation_tops array, one entry per formation):
- formation_name: Name of the formation
- md_ft: Measured Depth in feet to the formation top
- tvd_ft: True Vertical Depth in feet
- subsea_elevation_ft: Subsea elevation in feet
- pick_source: How the pick was determined (E-log, mud log, prognosis)

HYDROCARBON SHOWS (hydrocarbon_shows array, one entry per show interval):
- depth_from_ft: Top of the show interval in feet
- depth_to_ft: Bottom of the show interval in feet
- peak_gas_units: Maximum gas units recorded over the interval
- baseline_gas_units: Baseline or background gas units
- c1_ppm: Methane concentration in ppm
- c2_ppm: Ethane concentration in ppm
- c3_ppm: Propane concentration in ppm
- c4_ppm: Butane concentration in ppm
- c5_ppm: Pentane concentration in ppm
- fluorescence: Visual fluorescence description
- cut: Sample cut description
- lithology_description: Lithologic description of the interval
"""


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

CASING_PROMPT = """Extract casing, cementing, multi-stage tooling, and cement evaluation data from this wellfile PDF. Return ONLY a valid JSON object matching the provided schema. If a value is not found, set it to null. Use empty arrays when no data is available.

API Number: {api_number}

CASING PROGRAM (casing_program array, one entry per string):
- string_type: Type of string (Surface, Intermediate, Production, Liner)
- hole_size_in: Drilled hole size in inches
- casing_od_in: Casing outer diameter in inches
- nominal_weight_lbs_ft: Nominal weight in pounds per foot
- steel_grade: Steel grade designation
- connection_type: Thread or connection type
- setting_depth_ft: Setting depth in feet
- burst_rating_psi: Burst pressure rating
- collapse_rating_psi: Collapse pressure rating

CEMENTING OPERATIONS (cementing_operations array, one entry per job):
- slurry_volume_sacks: Volume of cement in sacks
- slurry_volume_bbls: Volume of cement in barrels
- lead_tail_formulation: Description of lead and tail slurry formulations
- slurry_density_ppg: Slurry density in pounds per gallon
- additives: Cement additives used
- displacement_volume_bbls: Displacement volume in barrels
- bump_pressure_psi: Bump pressure in PSI
- surface_return_volume_bbls: Volume of cement returns at surface in barrels

MULTI-STAGE TOOLS (multi_stage_tools array, one entry per tool):
- stage_tool_depth_ft: Stage/DV tool measured depth
- opening_pressure_psi: Tool opening pressure
- closing_pressure_psi: Tool closing pressure
- isolation_interval_from_ft: Stage isolation interval top
- isolation_interval_to_ft: Stage isolation interval bottom

CEMENT EVALUATION (cement_evaluation object):
- logged_toc_ft: Logged Top of Cement in feet
- verification_method: How the TOC was verified (Cement Bond Log, temperature survey, calculated)
- bond_assessment: Qualitative bond assessment across target pay zones
"""


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

DRILLING_PROMPT = """Extract drilling fluid parameters, bit performance data, and wellbore event records from this wellfile PDF. Return ONLY a valid JSON object matching the provided schema. If a value is not found, set it to null. Use empty arrays when no data is available.

API Number: {api_number}

DRILLING FLUID PARAMETERS (drilling_fluid_params array, one entry per depth interval):
- depth_ft: Depth of the fluid measurement in feet
- mud_type: Mud system type (water-based, oil-based invert, etc.)
- mud_weight_ppg: Mud weight in pounds per gallon
- funnel_viscosity_sec: Funnel viscosity in seconds
- fluid_loss_cc: Fluid loss or water loss in cc
- chlorides_ppm: Chloride concentration in ppm
- oil_water_ratio: Oil-to-water ratio

BIT RUNS (bit_runs array, one entry per bit run):
- bit_number: Sequential bit number
- bit_size_in: Bit diameter in inches
- manufacturer: Bit manufacturer name
- iadc_code: IADC bit code or cutter type description
- cutter_type: Cutter type (PDC, roller cone, etc.)
- depth_in_ft: Depth the bit went in (start depth)
- depth_out_ft: Depth the bit came out (end depth)
- rotating_hours: Total rotating hours on the bit
- footage_drilled_ft: Total footage drilled by the bit
- avg_rop_ft_per_hr: Average rate of penetration in feet per hour

WELLBORE EVENTS (wellbore_events array, one entry per event):
- event_type: Type of event (lost circulation, gas kick, tight hole, etc.)
- depth_ft: Depth where the event occurred
- description: Detailed description of the event
- treatment_type: Treatment or remediation applied
"""


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
