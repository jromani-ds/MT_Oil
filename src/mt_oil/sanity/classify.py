"""Treatment type classifier.

Consumes state data (rate, pressure) and FracFocus chemistry
to classify treatment as matrix acidizing, acid frac, hydraulic
fracture, energized, or foamed.
"""


def classify_treatment(
    has_acid: bool = False,
    has_gas: bool = False,
    total_proppant_lbs: float | None = None,
    max_treating_rate_bpm: float | None = None,
    max_treating_pressure_psi: float | None = None,
    fracture_gradient_psi_per_ft: float | None = None,
    tvd_ft: float | None = None,
    foam_quality_pct: float | None = None,
    acid_volume_gal: float | None = None,
    net_perforated_ft: float | None = None,
) -> tuple[str, str]:
    """Classify treatment type and return (classification, confidence_note).

    Classification strings:
        matrix_acidizing, acid_breakdown, acid_frac,
        hydraulic_fracture, energized, foam, mist, unknown
    """
    is_foam = foam_quality_pct is not None and foam_quality_pct > 0
    is_acid = has_acid
    is_gas = has_gas
    proppant_present = total_proppant_lbs is not None and total_proppant_lbs > 0

    # ── Foam / Energized (checked first) ──
    if is_foam:
        if foam_quality_pct >= 80:
            return "mist", f"Foam quality {foam_quality_pct:.0f}% → mist regime"
        elif foam_quality_pct >= 50:
            return "foam", f"Stable foam quality {foam_quality_pct:.0f}%"
        else:
            return "energized", f"Energized fluid, quality {foam_quality_pct:.0f}%"

    if is_gas and is_acid:
        return "acid_frac", "Gas + acid present; classified as acid frac"

    # ── Acid treatments ──
    if is_acid:
        # Acid breakdown / spearhead: low acid intensity (10–50 gal/ft)
        if (
            acid_volume_gal is not None
            and net_perforated_ft is not None
            and net_perforated_ft > 0
        ):
            acid_intensity = acid_volume_gal / net_perforated_ft
            if 10 <= acid_intensity < 50 and not proppant_present:
                return (
                    "acid_breakdown",
                    f"Acid intensity {acid_intensity:.0f} gal/ft in cleanup range → acid breakdown / spearhead",
                )
            if acid_intensity < 10 and not proppant_present:
                return (
                    "acid_breakdown",
                    f"Acid intensity {acid_intensity:.0f} gal/ft very low → acid breakdown / spearhead",
                )

        if proppant_present or (
            max_treating_rate_bpm is not None and max_treating_rate_bpm > 5
        ):
            return "acid_frac", "High rate or proppant present with acid → acid frac"
        if (
            max_treating_pressure_psi is not None
            and fracture_gradient_psi_per_ft is not None
            and tvd_ft is not None
        ):
            breakdown_pressure = fracture_gradient_psi_per_ft * tvd_ft
            hydrostatic = tvd_ft * 0.433
            if max_treating_pressure_psi >= (breakdown_pressure - hydrostatic) * 0.9:
                return "acid_frac", "Treating pressure near/above breakdown → acid frac"
        return (
            "matrix_acidizing",
            "Acid present, low rate, no proppant → matrix acidizing",
        )

    # ── Hydraulic fracturing ──
    if proppant_present or (
        max_treating_rate_bpm is not None and max_treating_rate_bpm > 5
    ):
        return (
            "hydraulic_fracture",
            "Proppant present or high rate → hydraulic fracture",
        )

    return "unknown", "Insufficient data to classify treatment"


def compute_foam_quality(
    gas_volume_downhole_gal: float | None,
    liquid_volume_gal: float | None,
) -> float | None:
    """Compute foam quality Q (%) = V_gas / (V_gas + V_liquid) × 100."""
    if gas_volume_downhole_gal is None or liquid_volume_gal is None:
        return None
    total = gas_volume_downhole_gal + liquid_volume_gal
    if total <= 0:
        return None
    return gas_volume_downhole_gal / total * 100.0
