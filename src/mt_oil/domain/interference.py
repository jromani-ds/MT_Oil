"""Parent-child well interference detection.

Uses wells table (lat/long) + optional GIS wellpaths for spatial proximity,
frac_focus job_start_date for child frac timing, and production_monthly
for offset production drops.
"""

import math
from datetime import datetime, timedelta

import pandas as pd


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters between two lat/lon points."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_offset_wells(
    api_number: str,
    wells_df: pd.DataFrame,
    radius_m: float = 1000.0,
) -> list[dict]:
    """Find offset wells within a given radius (meters) of the target well.

    Uses geodetic-datum-normalized projected UTM distances (handles mixed
    NAD27/NAD83 public records).

    wells_df: DataFrame with columns API_WellNo, latitude, longitude.
    Returns list of dicts with offset API, distance, and datum method.
    """
    if wells_df.empty:
        return []

    target = wells_df[wells_df["API_WellNo"] == api_number]
    if target.empty:
        return []

    target_lat = float(target.iloc[0]["latitude"])
    target_lon = float(target.iloc[0]["longitude"])
    target_datum = target.iloc[0].get("coordinate_datum") or "wgs84_assumed"

    offsets = []
    for _, row in wells_df.iterrows():
        if str(row["API_WellNo"]) == api_number:
            continue
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        offset_datum = row.get("coordinate_datum") or "wgs84_assumed"

        from mt_oil.domain import crs

        dist_m, method = crs.projected_distance(
            target_lat,
            target_lon,
            lat,
            lon,
            datum1=target_datum,
            datum2=offset_datum,
        )

        if dist_m <= radius_m:
            offsets.append(
                {
                    "api_wellno": str(row["API_WellNo"]),
                    "distance_m": round(dist_m, 1),
                    "distance_method": method,
                }
            )
    return sorted(offsets, key=lambda x: x["distance_m"])


def detect_frac_hits(
    child_api_number: str,
    child_frac_date: str,
    offsets: list[dict],
    prod_df: pd.DataFrame,
    window_months: int = 3,
) -> list[dict]:
    """Detect frac hits: production drops on offset wells within window after child frac.

    child_frac_date: JobStartDate from frac_focus (YYYY-MM-DD).
    prod_df: production data with columns API_WellNo, Rpt_Date, BBLS_OIL_COND,
             MCF_GAS, BBLS_WTR (optional).
    window_months: look for production drop within this many months after frac.

    Confidence scoring:
        - HIGH (≥0.7): oil drop >20% AND water cut increase >10 pp OR GOR drop >20%
        - MODERATE (0.4–0.7): oil drop >20% without corroborating water/GOR evidence
        - LOW (<0.4): oil drop <20% even with water/GOR evidence

    Returns list of frac hit events with confidence, mechanism, and delta fields.
    """
    if not offsets or prod_df.empty:
        return []

    try:
        frac_dt = datetime.strptime(child_frac_date[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return []

    # Tight window: ±60 days from frac date for high-confidence
    start_window = frac_dt
    end_window = frac_dt + timedelta(days=window_months * 30)
    # Baseline: 6 months prior to frac
    baseline_start = frac_dt - timedelta(days=180)

    hits = []
    for offset in offsets:
        offset_api = offset["api_wellno"]
        offset_prod = prod_df[prod_df["API_WellNo"] == offset_api].copy()
        if offset_prod.empty:
            continue

        offset_prod["Rpt_Date"] = pd.to_datetime(offset_prod["Rpt_Date"])

        # Production before frac (baseline)
        baseline = offset_prod[
            (offset_prod["Rpt_Date"] >= baseline_start)
            & (offset_prod["Rpt_Date"] < frac_dt)
        ]
        # Production after frac (window)
        after = offset_prod[
            (offset_prod["Rpt_Date"] >= start_window)
            & (offset_prod["Rpt_Date"] <= end_window)
        ]

        if baseline.empty or after.empty:
            continue

        baseline_oil = baseline["BBLS_OIL_COND"].mean()
        after_oil = after["BBLS_OIL_COND"].mean()
        baseline_gas = baseline["MCF_GAS"].mean()
        after_gas = after["MCF_GAS"].mean()

        oil_drop_pct = 0.0
        if baseline_oil > 0:
            oil_drop_pct = round((baseline_oil - after_oil) / baseline_oil * 100, 1)

        gas_drop_pct = 0.0
        if baseline_gas > 0:
            gas_drop_pct = round((baseline_gas - after_gas) / baseline_gas * 100, 1)

        # ── Water cut and GOR deltas (for mechanism corroboration) ──
        has_water = "BBLS_WTR" in after.columns and "BBLS_WTR" in baseline.columns
        water_cut_delta_pct = 0.0
        gor_delta_pct = 0.0
        if has_water:
            baseline_wtr = baseline["BBLS_WTR"].mean()
            after_wtr = after["BBLS_WTR"].mean()

            baseline_total = baseline_oil + baseline_wtr
            after_total = after_oil + after_wtr
            baseline_wc = (
                baseline_wtr / baseline_total * 100 if baseline_total > 0 else 0
            )
            after_wc = after_wtr / after_total * 100 if after_total > 0 else 0
            water_cut_delta_pct = round(after_wc - baseline_wc, 1)

            baseline_gor = baseline_gas / baseline_oil if baseline_oil > 0 else 0
            after_gor = after_gas / after_oil if after_oil > 0 else 0
            if baseline_gor > 0:
                gor_delta_pct = round(
                    (after_gor - baseline_gor) / baseline_gor * 100, 1
                )

        # ── Confidence scoring ──
        oil_drop_gt_20 = oil_drop_pct > 20
        wc_spike = water_cut_delta_pct > 10
        gor_drop = gor_delta_pct < -20

        if oil_drop_gt_20 and (wc_spike or gor_drop):
            confidence = 0.8
            mechanism = "frac_hit"
        elif oil_drop_gt_20:
            confidence = 0.5
            mechanism = "possible_interference"
        elif wc_spike or gor_drop:
            confidence = 0.3
            mechanism = "low_confidence"
        else:
            continue  # No significant change — skip

        hit = {
            "offset_api": offset_api,
            "distance_m": offset["distance_m"],
            "oil_drop_pct": oil_drop_pct,
            "gas_drop_pct": gas_drop_pct,
            "water_cut_delta_pct": water_cut_delta_pct,
            "gor_delta_pct": gor_delta_pct,
            "baseline_oil_bbls": round(baseline_oil, 1),
            "after_oil_bbls": round(after_oil, 1),
            "confidence": confidence,
            "mechanism": mechanism,
            "note": (
                f"Offset production dropped {oil_drop_pct}% oil / {gas_drop_pct}% gas "
                f"within {window_months} months of child frac. "
                f"Water cut {'+' if water_cut_delta_pct >= 0 else ''}{water_cut_delta_pct}pp, "
                f"GOR {'+' if gor_delta_pct >= 0 else ''}{gor_delta_pct}%. "
                f"Confidence: {confidence:.1f}"
            ),
        }
        hits.append(hit)

    return hits
