"""Monthly well PDF ingestion job.

This module is invoked as a Cloud Run Job to download well-report PDFs from the
Montana DNRC DataMiner for every API number in BigQuery, and store them in GCS
under the prefix wells/pdfs/{api_wellno}.pdf.

It is idempotent and incremental: each run skips wells whose PDF already exists
in GCS with a Content-Length matching the remote resource, only re-downloading
when the file size has changed.
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
DNRC_BASE_URL = "https://bogapps.dnrc.mt.gov/dataminer/Wells/WellData.aspx"
REQUEST_TIMEOUT = 60
DEFAULT_DELAY = 1.5
LOG_INTERVAL = 100
SKIP_EXTENSIONS = {".aspx", ".html", ".htm"}

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
    "Referer": "https://bogapps.dnrc.mt.gov/",
}


def _build_request(url: str, method: str = "GET") -> Request:
    req = Request(url, method=method, headers=BROWSER_HEADERS)
    return req


def _get_bq_api_numbers() -> list[str]:
    client = bigquery.Client(project=settings.gcp_project_id)
    table = f"`{settings.gcp_project_id}.{settings.bigquery_dataset}.wells`"
    query = f"SELECT DISTINCT api_wellno FROM {table} ORDER BY api_wellno"
    rows = client.query(query).result()
    return [str(row.api_wellno) for row in rows]


def _head_pdf_url(api_wellno: str) -> tuple[int | None, str | None]:
    url = f"{DNRC_BASE_URL}?Name={api_wellno}"
    req = _build_request(url, method="HEAD")
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            content_length = resp.headers.get("Content-Length")
            content_type = resp.headers.get("Content-Type", "").lower()
            return (
                int(content_length) if content_length else None,
                content_type or None,
            )
    except (HTTPError, URLError, OSError) as e:
        print(f"  HEAD failed for {api_wellno}: {e}")
        return None, None


def _download_pdf(api_wellno: str, dest: Path) -> bool:
    url = f"{DNRC_BASE_URL}?Name={api_wellno}"
    req = _build_request(url)
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            ct = (resp.headers.get("Content-Type") or "").lower()
            if "application/pdf" not in ct:
                print(f"  Skipping {api_wellno}: Content-Type={ct} (not PDF)")
                return False
            with open(dest, "wb") as f:
                shutil.copyfileobj(resp, f)
            if dest.stat().st_size == 0:
                print(f"  Skipping {api_wellno}: empty response body")
                dest.unlink(missing_ok=True)
                return False
            return True
    except (HTTPError, URLError, OSError) as e:
        print(f"  Download failed for {api_wellno}: {e}")
        return False


def _gcs_blob(api_wellno: str):
    client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_data_bucket)
    return bucket.blob(f"{PDF_PREFIX}{api_wellno}.pdf")


def _upload_pdf(api_wellno: str, local_path: Path) -> None:
    blob = _gcs_blob(api_wellno)
    blob.upload_from_filename(str(local_path))


def _gcs_pdf_size(api_wellno: str) -> int | None:
    blob = _gcs_blob(api_wellno)
    if blob.exists():
        blob.reload()
        return blob.size
    return None


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
    errors = 0
    start_time = time.time()

    for idx, api in enumerate(api_numbers, start=1):
        try:
            if idx % LOG_INTERVAL == 0:
                elapsed = time.time() - start_time
                print(
                    f"[{idx}/{len(api_numbers)}] "
                    f"fetched={fetched} skipped={skipped} errors={errors} "
                    f"elapsed={elapsed:.0f}s"
                )

            gcs_size = _gcs_pdf_size(api)

            remote_size, content_type = _head_pdf_url(api)

            if content_type and any(ext in content_type for ext in SKIP_EXTENSIONS):
                print(f"  Skipping {api}: unexpected Content-Type={content_type}")
                errors += 1
                time.sleep(delay)
                continue

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
                ok = _download_pdf(api, tmp_path)
                if not ok:
                    errors += 1
                    continue

                _upload_pdf(api, tmp_path)
                fetched += 1
                upload_size = tmp_path.stat().st_size
                print(
                    f"  Fetched {api} ({upload_size:,} bytes) "
                    f"-> gs://{settings.gcs_data_bucket}/{PDF_PREFIX}{api}.pdf"
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
    print(f"  Skipped:     {skipped:,}")
    print(f"  Errors:      {errors:,}")
    print(f"  Elapsed:     {elapsed:.0f}s ({elapsed/60:.1f}min)")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
