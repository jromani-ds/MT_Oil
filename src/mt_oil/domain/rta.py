"""Rate Transient Analysis scaffold.

Gleaned from sundry IP tests (single-point FTP) and monthly rates — the
production .tab files carry no pressure time series, so full RTA is limited.
"""

import numpy as np


def linear_flow_indicator(rate: np.ndarray, time_months: np.ndarray) -> dict | None:
    """Assess early-time linear flow from rate vs 1/sqrt(t) regression.

    Linear flow signature: q·t^0.5 approximates a constant in fracture-dominated flow.
    """
    if len(rate) < 6:
        return None
    t_safe = np.clip(time_months, 0.5, None)
    1.0 / np.sqrt(t_safe)
    q_rt = rate * np.sqrt(t_safe)

    # If q·sqrt(t) is stable (low std / mean), linear flow present
    mean_q = float(np.mean(q_rt))
    if mean_q <= 0:
        return None
    stability = float(np.std(q_rt) / mean_q)
    return {
        "linear_flow_diagnostic": (
            "linear" if stability < 0.4 else "transitional_or_boundary"
        ),
        "stability_ratio": round(stability, 3),
        "mean_q_sqrt_t": round(mean_q, 1),
        "note": (
            "Early linear flow (fracture-dominated drainage) — matches planar fracture response"
            if stability < 0.4
            else "Flow deviates from pure linear — check for boundary-dominated depletion or interference"
        ),
    }


def material_balance_time_flow_regime(
    cumulative_production: np.ndarray,
    rate: np.ndarray,
    pressure_drop_psi: float | None = None,
) -> dict | None:
    """Flow regime from normalized pressure vs material balance time.

    t_mb = Gp / q. Log-log slope ~0.5 → linear flow; slope ~1.0 → boundary-dominated.
    """
    if len(rate) < 10:
        return None
    rate_safe = np.clip(rate, 1e-6, None)
    t_mb = cumulative_production / rate_safe
    t_mb_safe = np.clip(t_mb, 1e-6, None)
    log_t = np.log(t_mb_safe)
    log_q = np.log(rate_safe)

    # Estimate slope of log(q) vs log(t_mb)
    slope = np.polyfit(log_t, log_q, 1)[0]
    regime = (
        "boundary_dominated"
        if slope >= 0.8
        else "transitional" if slope >= 0.3 else "linear"
    )
    return {
        "slope": round(float(slope), 3),
        "flow_regime": regime,
        "note": (
            "Boundary-dominated flow (depletion)"
            if regime == "boundary_dominated"
            else (
                "Linear flow regime (fracture-dominated)"
                if regime == "linear"
                else "Transitional flow"
            )
        ),
    }


def fracture_surface_area_proxy(
    rate_bbl_per_day: float,
    sqrt_k_md: float,
    viscosity_cp: float,
    total_compressibility_psi: float,
) -> float | None:
    """Ac·sqrt(k) proxy from linear-flow analysis (simplified).

    Returns a dimensional proxy proportional to fracture surface area.
    """
    if rate_bbl_per_day <= 0 or sqrt_k_md <= 0:
        return None
    # Simplified: Ac ∝ q / sqrt(k·μ·ct)  (from 1/√t linear flow constant)
    denom = sqrt_k_md * (viscosity_cp * total_compressibility_psi) ** 0.5
    return round(rate_bbl_per_day / denom, 3)
