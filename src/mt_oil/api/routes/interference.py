"""FastAPI route for parent-child well interference detection.

Uses existing wells and production tables in BigQuery for spatial
proximity and production-drop analysis. No Gemini extraction needed.
"""

import logging

import pandas as pd
from fastapi import APIRouter, HTTPException, Path, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from mt_oil.config import settings
from mt_oil.data.bigquery_loader import BigQueryDataLoader
from mt_oil.domain.interference import detect_frac_hits, find_offset_wells

logger = logging.getLogger(__name__)

int_limiter = Limiter(key_func=lambda r: get_remote_address(r))
router = APIRouter(prefix="/wells/{api_number}/interference", tags=["interference"])

_bq_loader: BigQueryDataLoader | None = None


def _get_loader() -> BigQueryDataLoader | None:
    global _bq_loader
    if _bq_loader is None and settings.gcp_project_id and settings.bigquery_dataset:
        _bq_loader = BigQueryDataLoader(
            settings.gcp_project_id, settings.bigquery_dataset
        )
    return _bq_loader


@router.get("")
@int_limiter.limit(settings.rate_limit)
def get_interference(
    request: Request,
    api_number: str = Path(..., title="API Well Number"),
    radius_m: float = 1000.0,
    tight_window: bool = True,
) -> dict:
    """Detect parent-child well interference events.

    Finds offset wells within a radius (meters) and checks for production
    drops within a tight window of the child well's FracFocus job date.

    Args:
        tight_window: If True, use a ±60-day tight window around the child
            frac date (high-confidence, filters out freeze-offs/pump failures).
            If False, uses a relaxed 90-day window.
    """
    loader = _get_loader()
    if not loader:
        raise HTTPException(status_code=503, detail="BigQuery not available")

    try:
        wells_df = loader.load_wells()
    except Exception as exc:
        logger.error("Failed to load wells for interference: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load well data")

    if wells_df.empty:
        return {"api_number": api_number, "offsets": [], "frac_hits": []}

    target = wells_df[wells_df["API_WellNo"] == api_number]
    if target.empty:
        raise HTTPException(status_code=404, detail="Well not found")

    # Tag each well's coordinate datum (NAD27 for pre-1990 spud dates)
    from mt_oil.domain import crs

    wells_df = wells_df.copy()
    wells_df["coordinate_datum"] = wells_df["Spud_Date"].apply(
        lambda d: crs.infer_datum_row(str(d) if pd.notna(d) else None)
    )

    # Find offsets (projected distance in UTM, datum-normalized)
    offsets = find_offset_wells(api_number, wells_df, radius_m=radius_m)

    # Get child frac date from FracFocus
    child_frac_date = None
    try:
        ff_data = loader.load_fracfocus_well(api_number)
        if ff_data:
            child_frac_date = ff_data.get("job_start_date")
    except Exception:
        pass

    # Detect frac hits
    frac_hits = []
    if offsets and child_frac_date:
        try:
            # Load production for all offset wells
            prod_df = loader.load_wells_production_for_api_list(
                [o["api_wellno"] for o in offsets]
            )
            window_months = 3 if tight_window else 4  # ~90 days relaxed
            frac_hits = detect_frac_hits(
                child_api_number=api_number,
                child_frac_date=child_frac_date,
                offsets=offsets,
                prod_df=prod_df,
                window_months=window_months,
            )
            # Keep only high/moderate confidence in tight mode
            if tight_window:
                frac_hits = [h for h in frac_hits if h.get("confidence", 0) >= 0.5]
        except Exception as exc:
            logger.warning("Frac hit detection failed for %s: %s", api_number, exc)

    return {
        "api_number": api_number,
        "target_lat": float(target.iloc[0]["Lat"]),
        "target_lon": float(target.iloc[0]["Long"]),
        "search_radius_m": radius_m,
        "tight_window": tight_window,
        "offsets": offsets,
        "frac_hits": frac_hits,
        "child_frac_date": child_frac_date,
    }
