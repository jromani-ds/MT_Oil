"""One-time seed script: load MT DNRC .tab files into BigQuery.

This script supports two source modes:

1. Local files (default): reads ``MT_HistoricalWellList.tab`` and
   ``MT_HistoricalWellProduction.tab`` from the repository root.
2. GCS source: reads the same files from ``gs://<bucket>/raw/seed/``.

When ``--all-datasets`` is used, both the dev and prod datasets are seeded from
*the same* in-memory DataFrames so they stay identical. Row-count assertions
after upload verify the two datasets match.

Usage examples::

    # Seed a single dataset from local files (legacy behavior)
    python scripts/seed_bigquery.py --project <GCP_PROJECT_ID> --dataset mt_oil_dev

    # Upload local files to GCS once, then seed both datasets from GCS
    python scripts/seed_bigquery.py \
        --project <GCP_PROJECT_ID> \
        --gcs-bucket <GCS_BUCKET_NAME> \
        --all-datasets \
        --upload-source

    # Re-seed both datasets from existing GCS files
    python scripts/seed_bigquery.py \
        --project <GCP_PROJECT_ID> \
        --gcs-bucket <GCS_BUCKET_NAME> \
        --all-datasets
"""

import argparse
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
from google.cloud import bigquery, storage

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_OBJECTS = {
    "wells": "MT_HistoricalWellList.tab",
    "production": "MT_HistoricalWellProduction.tab",
}

GCS_SEED_PREFIX = "raw/seed"

WELL_COLUMNS = [
    "API_WellNo",
    "CoName",
    "Well_Nm",
    "Status",
    "Type",
    "DTD",
    "Lat",
    "Long",
    "County",
    "Prod_Field",
    "Spudded",
    "Completed",
    "Slant",
]


def _blob_path(table_key: str) -> str:
    return f"{GCS_SEED_PREFIX}/{SOURCE_OBJECTS[table_key]}"


def upload_to_gcs(
    client: storage.Client, bucket_name: str, local_path: Path, table_key: str
) -> str:
    """Upload a local source file to the standard GCS seed path."""
    blob_name = _blob_path(table_key)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path))
    gcs_uri = f"gs://{bucket_name}/{blob_name}"
    print(f"Uploaded {local_path.name} to {gcs_uri}")
    return gcs_uri


def download_from_gcs(
    client: storage.Client, bucket_name: str, table_key: str, destination: Path
) -> str:
    """Download a source file from GCS to a local path."""
    blob_name = _blob_path(table_key)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    if not blob.exists():
        raise FileNotFoundError(
            f"GCS object gs://{bucket_name}/{blob_name} does not exist. "
            "Run with --upload-source first."
        )
    blob.download_to_filename(str(destination))
    return str(destination)


def resolve_source_files(
    gcp_project: str,
    gcs_bucket: str | None,
    upload_source: bool,
    temp_dir: Path,
) -> dict[str, Path]:
    """Return a mapping of table key to local file path for each source file."""
    local_paths: dict[str, Path] = {}

    if gcs_bucket is None:
        if upload_source:
            raise ValueError("--upload-source requires --gcs-bucket")
        for table_key, file_name in SOURCE_OBJECTS.items():
            local_path = PROJECT_ROOT / file_name
            if not local_path.exists():
                raise FileNotFoundError(f"Local source file not found: {local_path}")
            local_paths[table_key] = local_path
        return local_paths

    storage_client = storage.Client(project=gcp_project)
    for table_key, file_name in SOURCE_OBJECTS.items():
        local_path = PROJECT_ROOT / file_name
        if upload_source:
            if not local_path.exists():
                raise FileNotFoundError(
                    f"Cannot upload to GCS: local source file not found: {local_path}"
                )
            upload_to_gcs(storage_client, gcs_bucket, local_path, table_key)

        destination = temp_dir / file_name
        download_from_gcs(storage_client, gcs_bucket, table_key, destination)
        local_paths[table_key] = destination

    return local_paths


def load_wells(local_path: Path) -> pd.DataFrame:
    print("Loading well headers...")
    df = pd.read_csv(
        local_path,
        sep="\t",
        low_memory=False,
        usecols=WELL_COLUMNS,
    )
    df = df.rename(
        columns={
            "API_WellNo": "api_wellno",
            "CoName": "operator",
            "Well_Nm": "well_name",
            "Status": "status",
            "Type": "type",
            "DTD": "dtd",
            "Lat": "latitude",
            "Long": "longitude",
            "County": "county",
            "Prod_Field": "field",
            "Spudded": "spud_date",
            "Completed": "completion_date",
            "Slant": "slant",
        }
    )
    df["api_wellno"] = df["api_wellno"].astype(str)
    for col in ["dtd", "latitude", "longitude"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["spud_date", "completion_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    df["formation"] = None
    df["total_depth"] = df["dtd"]
    df["ingested_at"] = pd.Timestamp.utcnow()
    return df


def load_production(local_path: Path, sample: int | None = None) -> pd.DataFrame:
    print("Loading production data...")
    df = pd.read_csv(
        local_path,
        sep="\t",
        low_memory=False,
        nrows=sample,
    )
    df = df.rename(
        columns={
            "API_WellNo": "api_wellno",
            "Rpt_Date": "rpt_date",
            "ST_FMTN_CD": "st_fmtn_cd",
            "BBLS_OIL_COND": "bbls_oil_cond",
            "MCF_GAS": "mcf_gas",
            "BBLS_WTR": "bbls_wtr",
            "DAYS_PROD": "days_prod",
        }
    )
    df["api_wellno"] = df["api_wellno"].astype(str)
    df["rpt_date"] = pd.to_datetime(df["rpt_date"], errors="coerce").dt.date
    for col in ["bbls_oil_cond", "mcf_gas", "bbls_wtr"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["days_prod"] = (
        pd.to_numeric(df["days_prod"], errors="coerce").fillna(0).astype("Int64")
    )
    df["ingested_at"] = pd.Timestamp.utcnow()
    return df


def load_fracfocus() -> pd.DataFrame | None:
    """Load FracFocus data from local CSV/ZIP if available; otherwise skip."""
    print("Loading FracFocus data (optional)...")
    try:
        from mt_oil.data.loader import pull_ff_data
        from mt_oil.processing.features import preprocess_ff_data

        raw_ff, _ = pull_ff_data()
        df = preprocess_ff_data(raw_ff)
        df = df.reset_index()
        df = df.rename(
            columns={
                "API_WellNo": "api_wellno",
                "MassIngredient": "total_proppant",
                "TVD": "tvd",
                "TotalBaseWaterVolume": "total_water_volume",
            }
        )
        # Downselect / aggregate to match BQ schema.
        df = (
            df.groupby("api_wellno")
            .agg(
                {
                    "total_proppant": "sum",
                    "total_water_volume": "sum",
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
        df["ingested_at"] = pd.Timestamp.utcnow()
        return df
    except (ImportError, OSError, ValueError, zipfile.BadZipFile) as e:
        print(f"Skipping FracFocus seed: {e}")
        return None


def upload_table(
    client: bigquery.Client,
    dataset_id: str,
    table_name: str,
    df: pd.DataFrame,
    write_disposition: str = "WRITE_TRUNCATE",
) -> None:
    table_ref = f"{client.project}.{dataset_id}.{table_name}"
    print(f"Uploading {len(df):,} rows to {table_ref}...")
    job = client.load_table_from_dataframe(
        df,
        table_ref,
        job_config=bigquery.LoadJobConfig(
            write_disposition=write_disposition,
        ),
    )
    job.result()
    print(f"Loaded {job.output_rows:,} rows into {table_ref}.")


def get_table_count(client: bigquery.Client, dataset_id: str, table_name: str) -> int:
    query = f"SELECT COUNT(*) AS n FROM `{client.project}.{dataset_id}.{table_name}`"
    result = client.query(query).result()
    return next(result)[0]


def assert_dataset_counts_match(
    client: bigquery.Client,
    datasets: Sequence[str],
    tables: Sequence[str],
) -> None:
    for table_name in tables:
        counts = {}
        for dataset_id in datasets:
            counts[dataset_id] = get_table_count(client, dataset_id, table_name)

        values = set(counts.values())
        if len(values) != 1:
            details = ", ".join(f"{ds}={n:,}" for ds, n in counts.items())
            raise AssertionError(
                f"Row count mismatch for table '{table_name}': {details}"
            )

        print(
            f"Verified {table_name} row counts match: "
            f"{next(iter(values)):,} rows in each dataset."
        )


def seed_dataset(
    client: bigquery.Client,
    dataset_id: str,
    wells_df: pd.DataFrame,
    prod_df: pd.DataFrame,
    frac_df: pd.DataFrame | None,
) -> list[str]:
    """Upload tables to a single dataset and return the names of uploaded tables."""
    uploaded: list[str] = []

    upload_table(client, dataset_id, "wells", wells_df)
    uploaded.append("wells")

    upload_table(client, dataset_id, "production_monthly", prod_df)
    uploaded.append("production_monthly")

    if frac_df is not None:
        upload_table(client, dataset_id, "frac_focus", frac_df)
        uploaded.append("frac_focus")

    return uploaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed MT Oil BigQuery tables")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument(
        "--dataset",
        help="BigQuery dataset ID (e.g. mt_oil_dev). Mutually exclusive with --all-datasets.",
    )
    parser.add_argument(
        "--gcs-bucket",
        help="GCS bucket that holds source .tab files under raw/seed/.",
    )
    parser.add_argument(
        "--all-datasets",
        action="store_true",
        help="Seed both mt_oil_dev and mt_oil_prod from the same source files.",
    )
    parser.add_argument(
        "--upload-source",
        action="store_true",
        help="Upload local .tab files to --gcs-bucket before seeding.",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Optional row limit for production table (testing).",
    )
    args = parser.parse_args()

    if args.all_datasets and args.dataset:
        parser.error("--dataset and --all-datasets are mutually exclusive")

    if not args.all_datasets and not args.dataset:
        parser.error("One of --dataset or --all-datasets is required")

    if args.upload_source and not args.gcs_bucket:
        parser.error("--upload-source requires --gcs-bucket")

    datasets: list[str]
    if args.all_datasets:
        datasets = ["mt_oil_dev", "mt_oil_prod"]
    else:
        datasets = [args.dataset]

    bq_client = bigquery.Client(project=args.project)

    with tempfile.TemporaryDirectory(prefix="mt_oil_seed_") as tmp:
        tmp_path = Path(tmp)
        source_files = resolve_source_files(
            gcp_project=args.project,
            gcs_bucket=args.gcs_bucket,
            upload_source=args.upload_source,
            temp_dir=tmp_path,
        )

        wells_df = load_wells(source_files["wells"])
        prod_df = load_production(source_files["production"], sample=args.sample)
        frac_df = load_fracfocus()

        uploaded_tables: list[str] = ["wells", "production_monthly"]
        if frac_df is not None:
            uploaded_tables.append("frac_focus")

        for dataset_id in datasets:
            print(f"\nSeeding dataset {dataset_id}...")
            seed_dataset(bq_client, dataset_id, wells_df, prod_df, frac_df)

        if len(datasets) > 1:
            print("\nVerifying row counts match across datasets...")
            assert_dataset_counts_match(bq_client, datasets, uploaded_tables)

    print("\nSeed complete.")


if __name__ == "__main__":
    main()
