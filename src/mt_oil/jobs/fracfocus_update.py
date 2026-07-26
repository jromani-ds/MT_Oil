"""Monthly FracFocus ingestion job.

This module is invoked as a Cloud Run Job to refresh the `frac_focus` BigQuery
table from the public FracFocus digital download. It is intentionally simple,
stateless, and idempotent: each run truncates and reloads the table.
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from google.cloud import bigquery, storage

from mt_oil.config import settings
from mt_oil.data.loader import pull_ff_data
from mt_oil.processing.features import preprocess_ff_data


RAW_ARCHIVE_PREFIX = "raw/fracfocus/"


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _archive_raw_zip(local_zip_path: Path) -> str:
    """Upload the raw FracFocus ZIP to GCS for reproducibility."""
    if not settings.gcs_data_bucket:
        return ""

    client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_data_bucket)
    destination = f"{RAW_ARCHIVE_PREFIX}{_now_str()}/FracFocusCSV.zip"
    blob = bucket.blob(destination)
    blob.upload_from_filename(str(local_zip_path))
    return f"gs://{settings.gcs_data_bucket}/{destination}"


def _aggregate_fracfocus(raw_ff_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw FracFocus records to one row per API_WellNo."""
    # preprocess_ff_data already aggregates proppant/fluid by API and filters to
    # records where Purpose == 'Proppant'.
    df = preprocess_ff_data(raw_ff_df).reset_index()
    df = df.rename(
        columns={
            "API_WellNo": "api_wellno",
            "MassIngredient": "total_proppant",
            "TVD": "tvd",
            "TotalBaseWaterVolume": "total_water_volume",
            "TotalBaseNonWaterVolume": "total_nonwater_volume",
        }
    )
    df = (
        df.groupby("api_wellno")
        .agg(
            {
                "total_proppant": "sum",
                "total_water_volume": "sum",
                "total_nonwater_volume": "sum",
                "tvd": "first",
            }
        )
        .reset_index()
    )
    df["api_wellno"] = df["api_wellno"].astype(str)
    df["td"] = df["tvd"]
    df["job_start_date"] = None
    df["state"] = "MT"
    df["county"] = None
    df["ingested_at"] = datetime.now(timezone.utc)
    # Final column order must match BigQuery schema.
    return df[
        [
            "api_wellno",
            "job_start_date",
            "state",
            "county",
            "total_water_volume",
            "total_proppant",
            "td",
            "tvd",
            "ingested_at",
        ]
    ]


def _upload_to_bigquery(df: pd.DataFrame) -> None:
    client = bigquery.Client(project=settings.gcp_project_id)
    table_ref = f"{settings.gcp_project_id}.{settings.bigquery_dataset}.frac_focus"
    print(f"Uploading {len(df):,} FracFocus rows to {table_ref}...")
    job = client.load_table_from_dataframe(
        df,
        table_ref,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
    )
    job.result()
    print(f"Loaded {job.output_rows:,} rows.")


def run() -> None:
    print("Starting FracFocus update job...")
    print(f"Project: {settings.gcp_project_id}, Dataset: {settings.bigquery_dataset}")

    if not settings.gcp_project_id or not settings.bigquery_dataset:
        raise EnvironmentError(
            "GCP_PROJECT_ID and BIGQUERY_DATASET environment variables are required"
        )

    raw_ff, _ = pull_ff_data(state_name="Montana", keep_zip=True)
    zip_path = Path("FracFocusCSV.zip")
    try:
        df = _aggregate_fracfocus(raw_ff)

        # Archive the downloaded ZIP if a data bucket is configured.
        if zip_path.exists() and settings.gcs_data_bucket:
            archive_uri = _archive_raw_zip(zip_path)
            print(f"Archived raw ZIP to {archive_uri}")

        _upload_to_bigquery(df)
    finally:
        if zip_path.exists():
            zip_path.unlink()

    print("FracFocus update job complete.")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
