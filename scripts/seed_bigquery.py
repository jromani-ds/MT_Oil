"""One-time seed script: load local MT DNRC .tab files into BigQuery.

Usage:
    python scripts/seed_bigquery.py --project my-project-1508887546225 --dataset mt_oil_dev

This script is intended to be run from a developer workstation that already has
MT_HistoricalWellList.tab and MT_HistoricalWellProduction.tab downloaded.
"""

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd
from google.cloud import bigquery


PROJECT_ROOT = Path(__file__).resolve().parents[1]

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


def load_wells() -> pd.DataFrame:
    print("Loading well headers...")
    df = pd.read_csv(
        PROJECT_ROOT / "MT_HistoricalWellList.tab",
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


def load_production(sample: Optional[int] = None) -> pd.DataFrame:
    print("Loading production data...")
    df = pd.read_csv(
        PROJECT_ROOT / "MT_HistoricalWellProduction.tab",
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


def load_fracfocus() -> Optional[pd.DataFrame]:
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
    except Exception as e:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed MT Oil BigQuery tables")
    parser.add_argument("--project", default="my-project-1508887546225")
    parser.add_argument("--dataset", default="mt_oil_dev")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Optional row limit for production table (testing).",
    )
    args = parser.parse_args()

    client = bigquery.Client(project=args.project)

    wells_df = load_wells()
    upload_table(client, args.dataset, "wells", wells_df)

    prod_df = load_production(sample=args.sample)
    upload_table(client, args.dataset, "production_monthly", prod_df)

    frac_df = load_fracfocus()
    if frac_df is not None:
        upload_table(client, args.dataset, "frac_focus", frac_df)

    print("Seed complete.")


if __name__ == "__main__":
    main()
