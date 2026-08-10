"""Batch wellfile download and extraction job.

Queries BigQuery for horizontal oil wells with production data, downloads
missing wellfile PDFs from the Montana DNRC file server, and extracts
completion parameters via Gemini 2.5 Flash Lite. Results are cached in the
wellfile_parsed_metadata BigQuery table for fast subsequent lookups.

Usage:
    python -m mt_oil.jobs.batch_wellfile_extraction
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Optional, Set

from google.cloud import bigquery, storage

from mt_oil.agents.tools.document import (
    _check_bq_cache,
    _extract_with_gemini,
    _gcs_uri as doc_gcs_uri,
    _read_pdf_from_gcs,
    _write_to_bq,
)
from mt_oil.agents.telemetry import Timer, emit_agent_telemetry
from mt_oil.config import settings
from mt_oil.jobs.pdf_fetch import (
    _Counters,
    _download_pdf,
    _gcs_pdf_size,
    _head_pdf,
    _upload_pdf,
)

logger = logging.getLogger(__name__)

# --- Constants ---

HORIZONTAL_OIL_QUERY = """
    SELECT DISTINCT w.api_wellno
    FROM `{project}.{dataset}.wells` w
    JOIN `{project}.{dataset}.production_monthly` p
      ON w.api_wellno = p.api_wellno
    WHERE LOWER(w.slant) LIKE '%horizontal%'
      AND p.bbls_oil_cond > 0
    ORDER BY w.api_wellno
"""

DOWNLOAD_WORKERS = 5
EXTRACT_WORKERS = 2
DOWNLOAD_DELAY = 1.5
EXTRACT_DELAY = 0.5
LOG_INTERVAL = 50


def _get_target_wells() -> list[str]:
    """Get all horizontal oil wells with production from BigQuery."""
    client = bigquery.Client(project=settings.gcp_project_id)
    query = HORIZONTAL_OIL_QUERY.format(
        project=settings.gcp_project_id,
        dataset=settings.bigquery_dataset,
    )
    rows = client.query(query).result()
    return [str(row.api_wellno) for row in rows]


def _wells_missing_pdf(
    api_numbers: list[str], storage_client: Optional[storage.Client] = None
) -> Set[str]:
    """Return the subset of wells whose PDF is not yet in GCS."""
    if storage_client is None:
        storage_client = storage.Client(project=settings.gcp_project_id)
    missing: Set[str] = set()
    for api in api_numbers:
        size = _gcs_pdf_size(api, storage_client)
        if size is None:
            missing.add(api)
    return missing


def _wells_needing_extraction(api_numbers: list[str]) -> list[str]:
    """Return wells not yet cached in the wellfile_parsed_metadata table."""
    needing: list[str] = []
    for api in api_numbers:
        cached = _check_bq_cache(api)
        if cached is None:
            needing.append(api)
    return needing


def _download_phase(target_api_numbers: list[str]) -> None:
    """Download missing PDFs from the Montana DNRC file server."""
    print("=" * 60)
    print("PHASE 1: DOWNLOAD MISSING PDFS FROM DNRC")
    print("=" * 60)

    storage_client = storage.Client(project=settings.gcp_project_id)
    missing = _wells_missing_pdf(target_api_numbers, storage_client)
    print(f"Wells needing PDF download: {len(missing):,}")

    if not missing:
        print("All PDFs already in GCS. Skipping download phase.")
        return

    counters = _Counters()
    lock = Lock()
    start_time = time.time()
    total = len(missing)

    def log_status() -> None:
        elapsed = time.time() - start_time
        print(
            f"  [{counters.processed}/{total}] "
            f"fetched={counters.fetched} "
            f"no_file={counters.no_file} "
            f"errors={counters.errors} "
            f"elapsed={elapsed:.0f}s"
        )

    def worker(api: str) -> None:
        pdf_url, remote_size = _head_pdf(api)
        if pdf_url is None:
            with lock:
                counters.inc(no_file=1)
            counters.inc(processed=1)
            return

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            ok = _download_pdf(pdf_url, tmp_path)
            if not ok:
                raise RuntimeError("PDF download failed")
            _upload_pdf(api, tmp_path)
            upload_size = tmp_path.stat().st_size
            counters.inc(fetched=1)
            print(f"  Downloaded {api} ({upload_size:,} bytes)")
        except Exception as e:
            print(f"  Error downloading {api}: {e}")
            counters.inc(errors=1)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        time.sleep(DOWNLOAD_DELAY)
        counters.inc(processed=1)
        if counters.processed % LOG_INTERVAL == 0:
            with lock:
                if counters.processed % LOG_INTERVAL == 0:
                    log_status()

    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as executor:
        futures = {executor.submit(worker, api): api for api in missing}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"  Unhandled worker error: {e}")
                counters.inc(errors=1)

    elapsed = time.time() - start_time
    print(
        f"Download phase complete: {counters.fetched} fetched, "
        f"{counters.no_file} no_file, {counters.errors} errors "
        f"in {elapsed:.0f}s ({elapsed/60:.1f}min)"
    )


def _extraction_phase(target_api_numbers: list[str]) -> None:
    """Extract completion parameters via Gemini for all uncached wells."""
    print("=" * 60)
    print("PHASE 2: EXTRACT COMPLETION PARAMETERS VIA GEMINI")
    print("=" * 60)

    needing = _wells_needing_extraction(target_api_numbers)
    print(f"Wells needing extraction: {len(needing):,}")

    if not needing:
        print("All wells already cached in BigQuery. Skipping extraction phase.")
        return

    start_time = time.time()
    extracted = 0
    skipped = 0
    errors = 0

    for idx, api in enumerate(needing, 1):
        gcs_uri = doc_gcs_uri(api)
        pdf_bytes = _read_pdf_from_gcs(api)
        if pdf_bytes is None:
            print(f"  [{idx}/{len(needing)}] Skipping {api}: no PDF in GCS")
            skipped += 1
            continue

        timer = Timer()
        timer.__enter__()
        try:
            specs = _extract_with_gemini(api, pdf_bytes)
            specs["extraction_status"] = "SUCCESS"
            timer.__exit__()
            emit_agent_telemetry(
                api_number=api,
                gcs_uri=gcs_uri,
                input_tokens=None,
                output_tokens=None,
                latency_ms=timer.elapsed_ms,
                cache_hit=False,
            )
            _write_to_bq(api, specs, gcs_uri, timer)
            extracted += 1
            print(
                f"  [{idx}/{len(needing)}] Extracted {api} ({timer.elapsed_ms:.0f}ms)"
            )
        except Exception as e:
            timer.__exit__()
            print(f"  [{idx}/{len(needing)}] Error extracting {api}: {e}")
            errors += 1

        if idx % LOG_INTERVAL == 0:
            elapsed = time.time() - start_time
            print(
                f"  Progress: {idx}/{len(needing)} "
                f"extracted={extracted} errors={errors} "
                f"skipped={skipped} elapsed={elapsed:.0f}s"
            )

        time.sleep(EXTRACT_DELAY)

    elapsed = time.time() - start_time
    print(
        f"Extraction phase complete: {extracted} extracted, "
        f"{skipped} skipped, {errors} errors "
        f"in {elapsed:.0f}s ({elapsed/60:.1f}min)"
    )


def run() -> None:
    """Run the full batch download + extraction pipeline."""
    print("=" * 60)
    print("BATCH WELLFILE DOWNLOAD + EXTRACTION JOB")
    print("=" * 60)
    print(f"Project: {settings.gcp_project_id}")
    print(f"Dataset: {settings.bigquery_dataset}")
    print(f"GCS bucket: {settings.gcs_data_bucket}")

    if not settings.gcp_project_id or not settings.bigquery_dataset:
        raise EnvironmentError(
            "GCP_PROJECT_ID and BIGQUERY_DATASET environment variables are required"
        )

    if not settings.gcs_data_bucket:
        raise EnvironmentError("GCS_DATA_BUCKET environment variable is required")

    print("Querying BigQuery for target wells...")
    target_wells = _get_target_wells()
    print(f"Found {len(target_wells):,} horizontal oil wells with production")

    _download_phase(target_wells)
    _extraction_phase(target_wells)

    print("=" * 60)
    print("BATCH JOB COMPLETE")
    print("=" * 60)


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    try:
        run()
    except Exception as exc:
        logger.exception("Batch job failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
