"""BigQuery-backed data loaders for the MT Oil API.

These replace the local-tab-file loaders in deployed / cloud environments.
Local file loaders are still available via `mt_oil.data.loader` for development.
"""

from typing import Set, Tuple

import pandas as pd
from google.cloud import bigquery


class BigQueryDataLoader:
    """Loads MT Oil data from a BigQuery dataset."""

    def __init__(self, project_id: str, dataset_id: str):
        if not project_id or not dataset_id:
            raise ValueError("Both project_id and dataset_id are required")
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id)

    def _table(self, table_name: str) -> str:
        return f"`{self.project_id}.{self.dataset_id}.{table_name}`"

    def load_wells(self) -> pd.DataFrame:
        """Load well header data indexed by API_WellNo."""
        query = f"""
        SELECT
            api_wellno,
            well_name,
            operator,
            latitude,
            longitude,
            type,
            slant,
            dtd,
            total_depth,
            county,
            field,
            formation,
            spud_date,
            completion_date,
            status
        FROM {self._table('wells')}
        ORDER BY api_wellno
        """
        df = self.client.query(query).to_dataframe(create_bqstorage_client=False)
        df = df.rename(
            columns={
                "api_wellno": "API_WellNo",
                "well_name": "Well_Name",
                "operator": "Operator",
                "latitude": "Lat",
                "longitude": "Long",
                "type": "Type",
                "slant": "Slant",
                "dtd": "DTD",
                "total_depth": "Total_Depth",
                "county": "County",
                "field": "Field",
                "formation": "Formation",
                "spud_date": "Spud_Date",
                "completion_date": "Completion_Date",
                "status": "Status",
            }
        )
        df["API_WellNo"] = df["API_WellNo"].astype(str)
        return df

    def load_production_for_well(self, api_number: str) -> pd.DataFrame:
        """Load production history for a single well.

        Returns a DataFrame with columns matching the local loader format.
        """
        query = f"""
        SELECT
            rpt_date,
            st_fmtn_cd,
            bbls_oil_cond,
            mcf_gas,
            bbls_wtr,
            days_prod
        FROM {self._table('production_monthly')}
        WHERE api_wellno = @api_wellno
        ORDER BY rpt_date
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("api_wellno", "STRING", api_number)
            ]
        )
        df = self.client.query(query, job_config=job_config).to_dataframe(
            create_bqstorage_client=False
        )
        if df.empty:
            return df
        df = df.rename(
            columns={
                "rpt_date": "Rpt_Date",
                "st_fmtn_cd": "ST_FMTN_CD",
                "bbls_oil_cond": "BBLS_OIL_COND",
                "mcf_gas": "MCF_GAS",
                "bbls_wtr": "BBLS_WTR",
                "days_prod": "DAYS_PROD",
            }
        )
        df["API_WellNo"] = api_number
        df["Rpt_Date"] = pd.to_datetime(df["Rpt_Date"])
        return df

    def load_producing_wells_set(self) -> Set[str]:
        """Load the set of API_WellNo that have any positive oil or gas production."""
        query = f"""
        SELECT DISTINCT api_wellno
        FROM {self._table('production_monthly')}
        WHERE bbls_oil_cond > 0 OR mcf_gas > 0
        """
        df = self.client.query(query).to_dataframe(create_bqstorage_client=False)
        return set(df["api_wellno"].astype(str))

    def load_fracfocus(self) -> pd.DataFrame:
        """Load aggregated FracFocus completion data indexed by API_WellNo.

        The BigQuery `frac_focus` table stores pre-aggregated totals (one row per
        well). The returned DataFrame exposes the exact columns used by the ML
        feature engineering path so it can be used directly in place of the
        locally-preprocessed FracFocus DataFrame.
        """
        query = f"""
        SELECT
            api_wellno,
            total_water_volume,
            total_proppant,
            tvd
        FROM {self._table('frac_focus')}
        """
        df = self.client.query(query).to_dataframe(create_bqstorage_client=False)
        df = df.rename(
            columns={
                "api_wellno": "API_WellNo",
                "total_water_volume": "TotalBaseWaterVolume",
                "total_proppant": "MassIngredient",
                "tvd": "TVD",
            }
        )
        df["API_WellNo"] = df["API_WellNo"].astype(str)
        df["PercentHFJob"] = 100.0
        df["TotalBaseNonWaterVolume"] = 0.0
        df = df.set_index("API_WellNo")
        df = df[
            [
                "PercentHFJob",
                "MassIngredient",
                "TVD",
                "TotalBaseWaterVolume",
                "TotalBaseNonWaterVolume",
            ]
        ]
        return df


def load_all_from_bigquery(
    project_id: str, dataset_id: str
) -> Tuple[pd.DataFrame, Set[str]]:
    """Convenience helper: returns (wells_df, producing_wells_set)."""
    loader = BigQueryDataLoader(project_id, dataset_id)
    return loader.load_wells(), loader.load_producing_wells_set()
