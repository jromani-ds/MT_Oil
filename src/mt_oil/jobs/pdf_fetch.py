"""Monthly well PDF ingestion job.

This module is invoked as a Cloud Run Job to download well-report PDFs from the
Montana DNRC file server for every API number in BigQuery, and store them in GCS
under wells/pdfs/{api_wellno}/{api_10_digit}.pdf.

The PDF download URL follows a deterministic pattern:
  https://bogfiles.dnrc.mt.gov/Well_Data/{api[:10]}/{api[:10]}.pdf

The job is idempotent and incremental: it skips wells whose PDF already exists
in GCS with a matching Content-Length, only re-downloading when sizes differ.
Wells without a PDF on the DNRC server (404) are recorded as a no-file skip.
"""

import shutil
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from google.cloud import bigquery, storage

from mt_oil.config import settings


PDF_PREFIX = "wells/pdfs/"
BOGFILES_BASE = "https://bogfiles.dnrc.mt.gov/Well_Data"
REQUEST_TIMEOUT = 60
DEFAULT_DELAY = 1.5
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


def _build_request(url: str, method: str = "GET") -> Request:
    return Request(url, method=method, headers=BROWSER_HEADERS)


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


def _gcs_blob(api_wellno: str):
    client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_data_bucket)
    return bucket.blob(_gcs_blob_name(api_wellno))


def _gcs_pdf_size(api_wellno: str) -> int | None:
    blob = _gcs_blob(api_wellno)
    if blob.exists():
        blob.reload()
        return blob.size
    return None


def _upload_pdf(api_wellno: str, local_path: Path) -> None:
    blob = _gcs_blob(api_wellno)
    blob.upload_from_filename(str(local_path))


def run(
    delay: float = DEFAULT_DELAY,
    max_wells: int | None = None,
) -> None:
    print("Starting well PDF fetch job...")
    print(f"Project: {settings.gcp_project_id}")
    print(f"Dataset: {settings.bigquery_dataset}")
    print(f"GCS bucket: {settings.gcs_data_bucket}")
    print(f"Delay: {delay}s between requests")

    if not settings.gcp_project_id or not settings.bigquery_dataset:
        raise EnvironmentError(
            "GCP_PROJECT_ID and BIGQUERY_DATASET environment variables are required"
        )

    if not settings.gcs_data_bucket:
        raise EnvironmentError("GCS_DATA_BUCKET environment variable is required")

    print("Querying BigQuery for API numbers...")
    api_numbers = _get_bq_api_numbers()
    print(f"Found {len(api_numbers):,} unique wells in BigQuery")

    if max_wells:
        api_numbers = api_numbers[:max_wells]
        print(f"Limited to first {max_wells:,} wells for this run")

    fetched = 0
    skipped = 0
    no_file = 0
    errors = 0
    start_time = time.time()

    for idx, api in enumerate(api_numbers, start=1):
        try:
            if idx % LOG_INTERVAL == 0:
                elapsed = time.time() - start_time
                print(
                    f"[{idx}/{len(api_numbers)}] "
                    f"fetched={fetched} skipped={skipped} "
                    f"no_file={no_file} errors={errors} "
                    f"elapsed={elapsed:.0f}s"
                )

            pdf_url, remote_size = _head_pdf(api)

            if pdf_url is None:
                no_file += 1
                time.sleep(delay)
                continue

            gcs_size = _gcs_pdf_size(api)

            if (
                gcs_size is not None
                and remote_size is not None
                and gcs_size == remote_size
            ):
                skipped += 1
                time.sleep(delay)
                continue

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = Path(tmp.name)

            try:
                ok = _download_pdf(pdf_url, tmp_path)
                if not ok:
                    errors += 1
                    continue

                _upload_pdf(api, tmp_path)
                fetched += 1
                upload_size = tmp_path.stat().st_size
                print(
                    f"  Fetched {api} ({upload_size:,} bytes) "
                    f"-> gs://{settings.gcs_data_bucket}/{_gcs_blob_name(api)}"
                )
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

            time.sleep(delay)

        except Exception as e:
            print(f"  Error processing {api}: {e}")
            errors += 1
            time.sleep(delay)

    elapsed = time.time() - start_time
    print("=" * 60)
    print("Well PDF fetch job complete.")
    print(f"  Total wells: {len(api_numbers):,}")
    print(f"  Fetched:     {fetched:,}")
    print(f"  Skipped:     {skipped:,} (same size, unchanged)")
    print(f"  No file:     {no_file:,} (no PDF on DNRC)")
    print(f"  Errors:      {errors:,}")
    print(f"  Elapsed:     {elapsed:.0f}s ({elapsed/60:.1f}min)")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
