"""Monthly FracFocus ingestion job.

This module is invoked as a Cloud Run Job to refresh the `frac_focus` and
`frac_focus_detail` BigQuery tables from the public FracFocus digital download.
The ingestion is deterministic, stateless, and idempotent: each run truncates
and reloads both tables, with ingredient-level data classified by CAS/lookup.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from google.cloud import bigquery, storage

from mt_oil.config import settings
from mt_oil.data.loader import pull_ff_data
from mt_oil.fracfocus.service import classify_all_ff
from mt_oil.processing.features import preprocess_ff_data

RAW_ARCHIVE_PREFIX = "raw/fracfocus/"


def _now_str() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def _archive_raw_zip(local_zip_path: Path) -> str:
    if not settings.gcs_data_bucket:
        return ""
    client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_data_bucket)
    destination = f"{RAW_ARCHIVE_PREFIX}{_now_str()}/FracFocusCSV.zip"
    blob = bucket.blob(destination)
    blob.upload_from_filename(str(local_zip_path))
    return f"gs://{settings.gcs_data_bucket}/{destination}"


def _build_aggregate_df(
    raw_ff_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build two DataFrames:

    1. frac_focus_aggr: one row per well, extended with classified columns
       (legacy aggregate columns preserved for ML backward compat).
    2. frac_focus_detail: one row per ingredient, classified.
    """
    # ── Classify all FF data ──
    aggregates, detail_list = classify_all_ff(raw_ff_df)

    # ── Detail DataFrame ──
    detail_rows = []
    for d in detail_list:
        detail_rows.append(
            {
                "api_wellno": d.api_wellno,
                "cas_number": d.cas_number,
                "ingredient_name": d.ingredient_name,
                "supplier": d.supplier,
                "purpose": d.purpose,
                "trade_name": d.trade_name,
                "mass_lbs": d.mass_lbs,
                "percent_hfj": d.percent_hfj,
                "calculation_type": d.calculation_type,
                "job_start_date": d.job_start_date,
                "job_end_date": d.job_end_date,
                "operator": d.operator,
                "well_name": d.well_name,
                "ingested_at": datetime.now(UTC).isoformat(),
            }
        )
    detail_df = pd.DataFrame(detail_rows)

    # ── Aggregate DataFrame (one row per well) ──
    # Preserve legacy columns for ML backward compat
    legacy = preprocess_ff_data(raw_ff_df).reset_index()
    legacy = legacy.rename(
        columns={
            "API_WellNo": "api_wellno",
            "MassIngredient": "total_proppant",
            "TVD": "tvd",
            "TotalBaseWaterVolume": "total_water_volume",
            "TotalBaseNonWaterVolume": "total_nonwater_volume",
        }
    )
    legacy = (
        legacy.groupby("api_wellno")
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
    legacy["api_wellno"] = legacy["api_wellno"].astype(str)
    legacy["td"] = legacy["tvd"]
    legacy["state"] = "MT"
    legacy["county"] = None
    legacy["ingested_at"] = datetime.now(UTC)

    # Merge new classified columns
    classified_rows = []
    for api, agg in aggregates.items():
        classified_rows.append(
            {
                "api_wellno": api,
                "total_water_volume_gal": agg.total_water_volume_gal,
                "total_acid_gal": agg.total_acid_gal,
                "proppant_breakdown": (
                    json.dumps(agg.proppant_breakdown.model_dump(exclude_none=True))
                    if agg.proppant_breakdown
                    else None
                ),
                "additives": (
                    json.dumps(agg.additives.model_dump(exclude_none=True))
                    if agg.additives
                    else None
                ),
                "base_fluid_type": agg.base_fluid_type,
                "gas_n2_scf": next(
                    (g.volume_scf for g in agg.gas_components if g.type == "N2"), None
                ),
                "gas_co2_scf": next(
                    (g.volume_scf for g in agg.gas_components if g.type == "CO2"), None
                ),
                "job_start_date": agg.job_start_date,
                "job_end_date": agg.job_end_date,
                "operator": agg.operator,
                "well_name": agg.well_name,
            }
        )

    classified_df = pd.DataFrame(classified_rows)

    # Merge with legacy aggregate on api_wellno
    merged = legacy.merge(classified_df, on="api_wellno", how="left")

    # Fill N/A from classification into legacy columns where blank
    for col in ["job_start_date", "job_end_date", "operator", "well_name"]:
        if f"{col}_x" in merged.columns and f"{col}_y" in merged.columns:
            merged[col] = merged[f"{col}_y"].fillna(merged[f"{col}_x"])
            merged.drop(columns=[f"{col}_x", f"{col}_y"], inplace=True)

    merged["ingested_at"] = datetime.now(UTC)

    # Parse raw date strings (e.g. "3/30/2013 7:58:00 AM") to date objects
    # for BQ DATE column compatibility.
    for df_ in [merged, detail_df]:
        if not df_.empty:
            for col_ in ("job_start_date", "job_end_date"):
                if col_ in df_.columns:
                    df_[col_] = pd.to_datetime(df_[col_], errors="coerce").dt.date

    # Column order: legacy first for backward compat, new columns after
    base_cols = [
        "api_wellno",
        "job_start_date",
        "state",
        "county",
        "total_water_volume",
        "total_proppant",
        "td",
        "tvd",
        "total_nonwater_volume",
    ]
    # Add new columns that exist in merged
    extra_cols = [
        "total_water_volume_gal",
        "total_acid_gal",
        "proppant_breakdown",
        "additives",
        "base_fluid_type",
        "gas_n2_scf",
        "gas_co2_scf",
        "job_end_date",
        "operator",
        "well_name",
        "ingested_at",
    ]
    final_cols = [c for c in base_cols + extra_cols if c in merged.columns]
    return merged[final_cols], detail_df


def _upload_df(client: bigquery.Client, df: pd.DataFrame, table_ref: str) -> None:
    if df.empty:
        print(f"Skipping empty upload to {table_ref}")
        return
    print(f"Uploading {len(df):,} rows to {table_ref}...")
    job = client.load_table_from_dataframe(
        df,
        table_ref,
        job_config=bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema_update_options=["ALLOW_FIELD_ADDITION"],
        ),
    )
    job.result()
    print(f"Loaded {job.output_rows:,} rows.")


def run() -> None:
    print("Starting FracFocus update job...")
    print(f"Project: {settings.gcp_project_id}, Dataset: {settings.bigquery_dataset}")

    if not settings.gcp_project_id or not settings.bigquery_dataset:
        raise OSError(
            "GCP_PROJECT_ID and BIGQUERY_DATASET environment variables are required"
        )

    raw_ff, _ = pull_ff_data(state_name="Montana", keep_zip=True)
    zip_path = Path("FracFocusCSV.zip")

    try:
        agg_df, detail_df = _build_aggregate_df(raw_ff)

        if zip_path.exists() and settings.gcs_data_bucket:
            archive_uri = _archive_raw_zip(zip_path)
            print(f"Archived raw ZIP to {archive_uri}")

        client = bigquery.Client(project=settings.gcp_project_id)

        # Upload aggregate (frac_focus)
        agg_ref = f"{settings.gcp_project_id}.{settings.bigquery_dataset}.frac_focus"
        _upload_df(client, agg_df, agg_ref)

        # Upload detail (frac_focus_detail)
        detail_ref = (
            f"{settings.gcp_project_id}.{settings.bigquery_dataset}.frac_focus_detail"
        )
        _upload_df(client, detail_df, detail_ref)

    finally:
        if zip_path.exists():
            zip_path.unlink()

    print("FracFocus update job complete.")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
