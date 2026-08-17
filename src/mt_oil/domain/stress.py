"""Rock mechanics — DFIT/minifrac/step-rate stress and friction diagnostics."""

import numpy as np


def sigma_hmin(closure_pressure_psi: float) -> float:
    """Minimum horizontal stress ≈ fracture closure pressure."""
    return closure_pressure_psi


def stress_gradient(closure_pressure_psi: float, tvd_ft: float) -> float | None:
    """In-situ stress gradient (psi/ft)."""
    if tvd_ft is None or tvd_ft <= 0:
        return None
    return closure_pressure_psi / tvd_ft


LEAKOFF_SIGNALS = {
    "normal": {
        "en": "normal matrix leakoff",
        "evidence": ["normal", "matrix leakoff", "matrix lt"],
    },
    "pdl": {
        "en": "pressure-dependent leakoff (fissure dilation)",
        "evidence": [
            "pressure dependent",
            "pdl",
            "fissure",
            "dilation",
            "natural fracture",
        ],
    },
    "height_recession": {
        "en": "early height recession",
        "evidence": ["height recession", "recession", "tip extension"],
    },
}


def classify_leakoff(dfit_notes: str | None) -> str | None:
    """Classify leakoff type from DFIT notes text.

    Returns 'normal', 'pdl', or 'height_recession', or None if unknown.
    """
    if not dfit_notes:
        return None
    text = dfit_notes.lower().replace("-", " ")
    for key, info in LEAKOFF_SIGNALS.items():
        if any(ev.replace("-", " ") in text for ev in info["evidence"]):
            return key
    return None


def friction_split(step_rate_pairs: list[dict]) -> dict:
    """Split near-wellbore fiction into perforation (∝Q²) and tortuosity (∝Q^0.5).

    Args:
        step_rate_pairs: list of dicts with 'rate_bpm' and 'isip_psi'.

    Fits: ISIP_i = Pc + a·Q_i² + b·Q_i^0.5

    Returns a dict with a ``status`` key:
        - "computed": full two-parameter fit succeeded
        - "indeterminate": insufficient data (see ``reason``)

    Two-parameter least-squares requires at least 3 (rate, ISIP) pairs
    (3 unknowns: Pc, a, b). With fewer, the system is under-determined and
    the fit is not attempted.
    """
    if not step_rate_pairs:
        return {
            "status": "indeterminate",
            "reason": "No step-rate shut-in data available",
        }

    if len(step_rate_pairs) == 1:
        return {
            "status": "indeterminate",
            "reason": "Single-point ISIP only — requires multi-rate step-down (N≥3 rate-pressure pairs)",
        }

    if len(step_rate_pairs) < 3:
        return {
            "status": "indeterminate",
            "reason": "Insufficient step-down points (N<3) — requires multi-rate step-down for friction decomposition",
        }

    rates = np.array([p["rate_bpm"] for p in step_rate_pairs], dtype=float)
    isips = np.array([p["isip_psi"] for p in step_rate_pairs], dtype=float)

    if rates.size < 3 or isips.size < 3 or np.any(rates <= 0) or np.any(isips <= 0):
        return {
            "status": "indeterminate",
            "reason": "Invalid step-rate data (non-positive rate or ISIP values)",
        }

    # Fit ISIP = Pc + a·Q² + b·Q^0.5 via linear least squares
    X = np.column_stack([np.ones_like(rates), rates**2, np.sqrt(rates)])
    try:
        coefs, *_ = np.linalg.lstsq(X, isips, rcond=None)
    except np.linalg.LinAlgError:
        return {
            "status": "indeterminate",
            "reason": "Least-squares fit failed (ill-conditioned step-down data)",
        }

    pc, a, b = coefs
    return {
        "status": "computed",
        "closure_pressure_psi": float(np.clip(pc, 0, None)),
        "perf_friction_coef": float(a),  # ΔP_perf ∝ Q²
        "nwb_tortuosity_coef": float(b),  # ΔP_NWB ∝ Q^0.5
        "fit_rate_bpm": float(rates[-1]),
    }


def fracture_gradient_pressure(
    surface_pressure_psi: float, tvd_ft: float, fluid_sg: float = 1.0
) -> float | None:
    """Apparent fracture gradient from surface treating pressure."""
    if tvd_ft is None or tvd_ft <= 0:
        return None
    bhp = surface_pressure_psi + 0.433 * fluid_sg * tvd_ft
    return bhp / tvd_ft
