"""BigQuery production data ADK tool.

Fetches historical monthly production volumes and runs DCA for a given API number.
"""

import logging

import numpy as np

from mt_oil.config import settings
from mt_oil.data.bigquery_loader import BigQueryDataLoader
from mt_oil.domain.decline_curve import fit_best_decline

logger = logging.getLogger(__name__)

_bq_loader: BigQueryDataLoader | None = None


def _get_loader() -> BigQueryDataLoader | None:
    global _bq_loader
    if _bq_loader is None and settings.gcp_project_id and settings.bigquery_dataset:
        _bq_loader = BigQueryDataLoader(
            settings.gcp_project_id, settings.bigquery_dataset
        )
    return _bq_loader


def bq_production_tool(api_number: str) -> dict:
    """Fetch historical monthly production and DCA parameters for a well from BigQuery.

    Args:
        api_number: The 10 or 14 digit API well number.

    Returns:
        A dict with 'total_months', 'peak_oil_bbls', 'peak_gas_mcf',
        'eur_boe', 'dca_method', and monthly production arrays.
    """
    loader = _get_loader()
    if loader is None:
        return {"error": "BigQuery not configured", "total_months": 0}

    df = loader.load_production_for_well(api_number)
    if df.empty:
        return {
            "total_months": 0,
            "peak_oil_bbls": 0,
            "peak_gas_mcf": 0,
            "eur_boe": None,
            "dca_method": None,
        }

    df = df[df["BBLS_OIL_COND"] > 0].reset_index(drop=True)
    if df.empty:
        return {
            "total_months": 0,
            "peak_oil_bbls": 0,
            "peak_gas_mcf": 0,
            "eur_boe": None,
            "dca_method": None,
        }

    result = {
        "total_months": int(len(df)),
        "peak_oil_bbls": float(df["BBLS_OIL_COND"].max()),
        "peak_gas_mcf": float(df["MCF_GAS"].max()),
        "eur_boe": None,
        "dca_method": None,
    }

    if len(df) >= 6:
        try:
            df["Month_Index"] = (
                df["Rpt_Date"] - df["Rpt_Date"].min()
            ).dt.days // 30 + 1
            t_months = df["Month_Index"].values.astype(float)
            q_oil = df["BBLS_OIL_COND"].values.astype(float)

            best_fit = fit_best_decline(t_months, q_oil, method="auto")
            if best_fit["method"]:
                result["dca_method"] = best_fit["method"]
                FORECAST_MONTHS = 24
                last_t = t_months[-1]
                forecast_t = np.arange(last_t + 1, last_t + FORECAST_MONTHS + 1)

                from mt_oil.domain.decline_curve import (
                    arps_decline,
                    duong_decline,
                )

                if best_fit["method"] == "arps":
                    forecast_q = arps_decline(forecast_t, **best_fit["params"])
                elif best_fit["method"] == "duong":
                    forecast_q = duong_decline(forecast_t, **best_fit["params"])
                else:
                    forecast_q = np.zeros_like(forecast_t)

                result["eur_boe"] = float(np.sum(forecast_q) + np.sum(q_oil))
        except Exception as exc:
            logger.warning("DCA fitting failed for %s: %s", api_number, exc)

    return result
