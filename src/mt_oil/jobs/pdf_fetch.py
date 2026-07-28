"""Monthly well PDF ingestion job.

This module is invoked as a Cloud Run Job to download well-report PDFs from the
Montana DNRC file server for every API number in BigQuery, and store them in GCS
under wells/pdfs/{api_wellno}/{api_10_digit}.pdf.

The PDF download URL follows a deterministic pattern:
  https://bogfiles.dnrc.mt.gov/Well_Data/{api[:10]}/{api[:10]}.pdf

The job is idempotent and incremental.  Progress for each Cloud Run execution is
persisted to a BigQuery table, so if a task is retried it resumes from the last
completed well instead of starting over.  Within an execution the job skips wells
whose PDF already exists in GCS with a matching Content-Length, only re-fetching
when sizes differ.  Wells without a PDF on the DNRC server (404) are recorded as
a no-file skip.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from google.cloud import bigquery, storage

from mt_oil.config import settings


PDF_PREFIX = "wells/pdfs/"
BOGFILES_BASE = "https://bogfiles.dnrc.mt.gov/Well_Data"
REQUEST_TIMEOUT = 60
DEFAULT_DELAY = 1.5
DEFAULT_MAX_WORKERS = 5
DEFAULT_MAX_ATTEMPTS = 3
LOG_INTERVAL = 100


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


class _Counters:
    """Thread-safe counters for run statistics."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.processed = 0
        self.fetched = 0
        self.skipped = 0
        self.no_file = 0
        self.errors = 0
        self.already_done = 0
        self.start_time = time.time()

    def inc(self, **kwargs: int) -> None:
        with self.lock:
            for key, value in kwargs.items():
                setattr(self, key, getattr(self, key) + value)


def _build_request(url: str, method: str = "GET") -> Request:
    return Request(url, method=method, headers=BROWSER_HEADERS)


def _execution_id() -> str:
    """Return a stable identifier for this Cloud Run execution.

    Retries of the same Cloud Run execution reuse ``CLOUD_RUN_EXECUTION`` so the
    job can resume from BigQuery.  Manual/local runs use ``EXECUTION_ID`` or a
    timestamped fallback.
    """
    return (
        os.environ.get("CLOUD_RUN_EXECUTION")
        or os.environ.get("EXECUTION_ID")
        or f"manual-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    )


def _status_table() -> str:
    """Fully-qualified BigQuery table name for progress tracking."""
    table = os.environ.get("PDF_FETCH_STATUS_TABLE", "pdf_fetch_status")
    return f"`{settings.gcp_project_id}.{settings.bigquery_dataset}.{table}`"


def _get_bq_api_numbers() -> list[str]:
    client = bigquery.Client(project=settings.gcp_project_id)
    table = f"`{settings.gcp_project_id}.{settings.bigquery_dataset}.wells`"
    query = f"SELECT DISTINCT api_wellno FROM {table} ORDER BY api_wellno"
    rows = client.query(query).result()
    return [str(row.api_wellno) for row in rows]


def _pdf_url(api_wellno: str) -> str | None:
    """Build the direct PDF URL from the first 10 digits of the API number.

    Returns None if the api_wellno is too short to extract 10 digits.
    """
    clean = api_wellno.strip()
    api_10 = clean[:10]
    if len(api_10) < 10:
        return None
    return f"{BOGFILES_BASE}/{api_10}/{api_10}.pdf"


def _head_pdf(api_wellno: str) -> tuple[str | None, int | None]:
    """HEAD the direct PDF URL to check for existence and size.

    Returns (pdf_url, size_bytes).  If the well has no PDF (404) or the
    api_wellno is invalid, returns (None, None).
    """
    url = _pdf_url(api_wellno)
    if not url:
        return None, None

    req = _build_request(url, method="HEAD")
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            cl = resp.headers.get("Content-Length")
            return url, int(cl) if cl else None
    except HTTPError as e:
        if e.code == 404:
            return None, None
        print(f"  HEAD failed ({e.code}) for {api_wellno}: {url}")
        return None, None
    except (URLError, OSError) as e:
        print(f"  HEAD failed for {api_wellno}: {e}")
        return None, None


def _download_pdf(pdf_url: str, dest: Path) -> bool:
    """Download a PDF from the given bogfiles URL.

    Returns True on success, False on failure (wrong content-type, empty body,
    or network error).
    """
    req = _build_request(pdf_url)
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            ct = (resp.headers.get("Content-Type") or "").lower()
            if "application/pdf" not in ct:
                print(f"  Skipping: Content-Type={ct} (not PDF)")
                return False
            with open(dest, "wb") as f:
                shutil.copyfileobj(resp, f)
            if dest.stat().st_size == 0:
                print("  Skipping: empty response body")
                dest.unlink(missing_ok=True)
                return False
            return True
    except (HTTPError, URLError, OSError) as e:
        print(f"  Download failed: {e}")
        return False


def _gcs_blob_name(api_wellno: str) -> str:
    clean = api_wellno.strip()[:10]
    return f"{PDF_PREFIX}{api_wellno}/{clean}.pdf"


def _gcs_blob(api_wellno: str, client: storage.Client | None = None):
    if client is None:
        client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_data_bucket)
    return bucket.blob(_gcs_blob_name(api_wellno))


def _gcs_pdf_size(api_wellno: str, client: storage.Client | None = None) -> int | None:
    blob = _gcs_blob(api_wellno, client)
    if blob.exists():
        blob.reload()
        return blob.size
    return None


def _upload_pdf(
    api_wellno: str, local_path: Path, client: storage.Client | None = None
) -> None:
    blob = _gcs_blob(api_wellno, client)
    blob.upload_from_filename(str(local_path))


def _load_progress(bq_client: bigquery.Client, execution_id: str) -> dict[str, dict]:
    """Load the progress rows BigQuery already has for this execution."""
    query = (
        f"SELECT api_wellno, status, size_bytes, attempts "
        f"FROM {_status_table()} WHERE execution_id = @execution_id"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("execution_id", "STRING", execution_id)
        ]
    )
    progress: dict[str, dict] = {}
    for row in bq_client.query(query, job_config=job_config).result():
        progress[row.api_wellno] = {
            "status": row.status,
            "size_bytes": row.size_bytes,
            "attempts": row.attempts or 0,
        }
    return progress


def _save_progress(
    bq_client: bigquery.Client,
    lock: threading.Lock,
    api_wellno: str,
    execution_id: str,
    status: str,
    size_bytes: int | None,
    attempts: int,
    error_message: str | None,
) -> None:
    """Upsert a progress row in BigQuery."""
    query = f"""
    MERGE {_status_table()} T
    USING (
      SELECT
        @api_wellno AS api_wellno,
        @execution_id AS execution_id,
        @status AS status,
        @size_bytes AS size_bytes,
        @updated_at AS updated_at,
        @attempts AS attempts,
        @error_message AS error_message
    ) S
    ON T.api_wellno = S.api_wellno AND T.execution_id = S.execution_id
    WHEN MATCHED THEN UPDATE SET
      status = S.status,
      size_bytes = S.size_bytes,
      updated_at = S.updated_at,
      attempts = S.attempts,
      error_message = S.error_message
    WHEN NOT MATCHED THEN INSERT (
      api_wellno, execution_id, status, size_bytes, updated_at, attempts, error_message
    ) VALUES (
      S.api_wellno, S.execution_id, S.status, S.size_bytes, S.updated_at, S.attempts,
      S.error_message
    )
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("api_wellno", "STRING", api_wellno),
            bigquery.ScalarQueryParameter("execution_id", "STRING", execution_id),
            bigquery.ScalarQueryParameter("status", "STRING", status),
            bigquery.ScalarQueryParameter(
                "size_bytes", "INT64", size_bytes if size_bytes is not None else None
            ),
            bigquery.ScalarQueryParameter(
                "updated_at", "TIMESTAMP", datetime.now(timezone.utc)
            ),
            bigquery.ScalarQueryParameter("attempts", "INT64", attempts),
            bigquery.ScalarQueryParameter("error_message", "STRING", error_message),
        ]
    )
    try:
        with lock:
            bq_client.query(query, job_config=job_config).result()
    except Exception as e:
        print(f"  Failed to persist progress for {api_wellno}: {e}")


def _process_well(
    api_wellno: str,
    progress: dict[str, dict],
    execution_id: str,
    bq_client: bigquery.Client,
    storage_client: storage.Client,
    counters: _Counters,
    lock: threading.Lock,
    delay: float,
    max_attempts: int,
) -> None:
    """Process a single well: skip if already done, otherwise HEAD/download/upload."""
    try:
        prior = progress.get(api_wellno)
        attempts = 1

        if prior is not None:
            prior_status = prior.get("status")
            if prior_status in ("fetched", "no_file"):
                counters.inc(already_done=1)
                return
            if prior_status == "error":
                prior_attempts = prior.get("attempts", 0) or 0
                if prior_attempts >= max_attempts:
                    counters.inc(already_done=1)
                    return
                attempts = prior_attempts + 1

        pdf_url, remote_size = _head_pdf(api_wellno)

        if pdf_url is None:
            counters.inc(no_file=1)
            _save_progress(
                bq_client,
                lock,
                api_wellno,
                execution_id,
                "no_file",
                None,
                attempts,
                None,
            )
            time.sleep(delay)
            counters.inc(processed=1)
            return

        gcs_size = _gcs_pdf_size(api_wellno, storage_client)

        if gcs_size is not None and remote_size is not None and gcs_size == remote_size:
            counters.inc(skipped=1)
            _save_progress(
                bq_client,
                lock,
                api_wellno,
                execution_id,
                "fetched",
                gcs_size,
                attempts,
                None,
            )
            time.sleep(delay)
            counters.inc(processed=1)
            return

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            ok = _download_pdf(pdf_url, tmp_path)
            if not ok:
                raise RuntimeError("PDF download failed")

            _upload_pdf(api_wellno, tmp_path, storage_client)
            upload_size = tmp_path.stat().st_size
            counters.inc(fetched=1)
            _save_progress(
                bq_client,
                lock,
                api_wellno,
                execution_id,
                "fetched",
                upload_size,
                attempts,
                None,
            )
            print(
                f"  Fetched {api_wellno} ({upload_size:,} bytes) "
                f"-> gs://{settings.gcs_data_bucket}/{_gcs_blob_name(api_wellno)}"
            )
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        time.sleep(delay)
        counters.inc(processed=1)

    except Exception as e:
        print(f"  Error processing {api_wellno}: {e}")
        error_message = str(e)[:512]
        try:
            _save_progress(
                bq_client,
                lock,
                api_wellno,
                execution_id,
                "error",
                None,
                attempts,
                error_message,
            )
        except Exception as save_error:
            print(f"  Could not save error progress for {api_wellno}: {save_error}")
        counters.inc(errors=1)
        time.sleep(delay)


def run(
    delay: float = DEFAULT_DELAY,
    max_wells: int | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> None:
    print("Starting well PDF fetch job...")
    print(f"Project: {settings.gcp_project_id}")
    print(f"Dataset: {settings.bigquery_dataset}")
    print(f"GCS bucket: {settings.gcs_data_bucket}")
    print(f"Delay: {delay}s per worker")
    print(f"Workers: {max_workers}")
    print(f"Max attempts per well: {max_attempts}")

    if not settings.gcp_project_id or not settings.bigquery_dataset:
        raise EnvironmentError(
            "GCP_PROJECT_ID and BIGQUERY_DATASET environment variables are required"
        )

    if not settings.gcs_data_bucket:
        raise EnvironmentError("GCS_DATA_BUCKET environment variable is required")

    execution_id = _execution_id()
    print(f"Execution ID: {execution_id}")

    print("Loading progress for this execution from BigQuery...")
    bq_client = bigquery.Client(project=settings.gcp_project_id)
    progress = _load_progress(bq_client, execution_id)
    print(f"Found {len(progress):,} wells already processed for this execution")

    print("Querying BigQuery for API numbers...")
    api_numbers = _get_bq_api_numbers()
    print(f"Found {len(api_numbers):,} unique wells in BigQuery")

    if max_wells:
        api_numbers = api_numbers[:max_wells]
        print(f"Limited to first {max_wells:,} wells for this run")

    total = len(api_numbers)
    counters = _Counters()
    lock = threading.Lock()

    def _log_status() -> None:
        elapsed = time.time() - counters.start_time
        print(
            f"[{counters.processed}/{total}] "
            f"fetched={counters.fetched} skipped={counters.skipped} "
            f"already_done={counters.already_done} no_file={counters.no_file} "
            f"errors={counters.errors} elapsed={elapsed:.0f}s"
        )

    def _worker(api: str) -> None:
        # Each worker gets its own cloud clients to avoid thread-safety issues.
        worker_bq_client = bigquery.Client(project=settings.gcp_project_id)
        worker_storage_client = storage.Client(project=settings.gcp_project_id)
        _process_well(
            api,
            progress,
            execution_id,
            worker_bq_client,
            worker_storage_client,
            counters,
            lock,
            delay,
            max_attempts,
        )

        # Throttled logging after each well.
        if counters.processed % LOG_INTERVAL == 0:
            with lock:
                if counters.processed % LOG_INTERVAL == 0:
                    _log_status()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_worker, api): api for api in api_numbers}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"  Unhandled worker error for {futures[future]}: {e}")
                counters.inc(errors=1)

    elapsed = time.time() - counters.start_time
    print("=" * 60)
    print("Well PDF fetch job complete.")
    print(f"  Total wells: {total:,}")
    print(f"  Fetched:     {counters.fetched:,}")
    print(f"  Skipped:     {counters.skipped:,} (same size, unchanged)")
    print(f"  Already done:{counters.already_done:,} (resumed from BigQuery)")
    print(f"  No file:     {counters.no_file:,} (no PDF on DNRC)")
    print(f"  Errors:      {counters.errors:,}")
    print(f"  Elapsed:     {elapsed:.0f}s ({elapsed / 60:.1f}min)")

    if counters.errors > 0:
        print("Exiting with error code due to processing failures.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch well PDFs from DNRC")
    parser.add_argument(
        "--delay",
        type=float,
        default=float(os.environ.get("PDF_FETCH_DELAY", DEFAULT_DELAY)),
        help="Seconds to wait between requests in each worker",
    )
    parser.add_argument(
        "--max-wells",
        type=int,
        default=int(os.environ.get("PDF_FETCH_MAX_WELLS", 0)) or None,
        help="Limit the number of wells to process",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=int(os.environ.get("PDF_FETCH_MAX_WORKERS", DEFAULT_MAX_WORKERS)),
        help="Number of concurrent download workers",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=int(os.environ.get("PDF_FETCH_MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS)),
        help="Maximum retry attempts per well within an execution",
    )
    args = parser.parse_args()
    run(
        delay=args.delay,
        max_wells=args.max_wells,
        max_workers=args.max_workers,
        max_attempts=args.max_attempts,
    )


if __name__ == "__main__":
    main()
