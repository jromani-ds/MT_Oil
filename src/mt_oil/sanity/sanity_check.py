"""Engineering Sanity Check — Rules 1–8.

These are pure functions that return lists of SanityFinding.
"""

from mt_oil.sanity.schemas import SanityFinding

# ── Rule 1: Proppant-to-Water Concentration (PPA) ────────────────────────────


def check_ppa(
    proppant_lbs: float | None,
    clean_water_gal: float | None,
    treatment_class: str | None = None,
    is_foam: bool = False,
    foam_quality_pct: float | None = None,
) -> list[SanityFinding]:
    findings: list[SanityFinding] = []

    is_acid_only = treatment_class in ("matrix_acidizing", "acid_breakdown")
    if is_acid_only:
        if proppant_lbs is None or proppant_lbs == 0:
            findings.append(
                SanityFinding(
                    rule="PPA",
                    severity="green",
                    message="Zero proppant validated for acid-only treatment",
                    raw_value=0.0,
                )
            )
            return findings
        else:
            findings.append(
                SanityFinding(
                    rule="PPA",
                    severity="red",
                    message=f"Proppant ({proppant_lbs:,.0f} lbs) reported on acid-only treatment — possible cross-stage data pollution",
                    raw_value=proppant_lbs,
                )
            )
            return findings

    if proppant_lbs is None or clean_water_gal is None or clean_water_gal <= 0:
        return findings

    ppa = proppant_lbs / clean_water_gal

    if is_foam and foam_quality_pct is not None:
        q = foam_quality_pct / 100.0
        ppa_foam = ppa * (1.0 - q)
        if ppa > 12.0:
            findings.append(
                SanityFinding(
                    rule="PPA",
                    severity="red",
                    message=f"Liquid PPA {ppa:.2f} exceeds blender/tub limit of 12.0 — possible unit error",
                    raw_value=ppa,
                )
            )
        if ppa_foam > 4.0:
            findings.append(
                SanityFinding(
                    rule="PPA",
                    severity="red",
                    message=f"Downhole foam PPA {ppa_foam:.2f} exceeds fracture transport limit of 4.0",
                    raw_value=ppa_foam,
                )
            )
        elif ppa_foam < 0.5:
            findings.append(
                SanityFinding(
                    rule="PPA",
                    severity="yellow",
                    message=f"Downhole foam PPA {ppa_foam:.2f} below typical 0.5 — possible transport issue",
                    raw_value=ppa_foam,
                )
            )
        else:
            findings.append(
                SanityFinding(
                    rule="PPA",
                    severity="green",
                    message=f"PPA_liquid={ppa:.2f}, PPA_foam={ppa_foam:.2f} within bounds",
                )
            )
        return findings

    if ppa > 10.0:
        findings.append(
            SanityFinding(
                rule="PPA",
                severity="red",
                message=f"PPA {ppa:.2f} > 10.0 — critical unit error (metric tons entered as lbs?)",
                raw_value=ppa,
            )
        )
    elif ppa < 0.1:
        findings.append(
            SanityFinding(
                rule="PPA",
                severity="red",
                message=f"PPA {ppa:.2f} < 0.1 — critical unit error (bbl mixed with gal?)",
                raw_value=ppa,
            )
        )
    else:
        in_slickwater = 0.25 <= ppa <= 2.5
        in_gel = 1.0 <= ppa <= 8.0
        if in_slickwater or in_gel:
            findings.append(
                SanityFinding(
                    rule="PPA",
                    severity="green",
                    message=f"PPA {ppa:.2f} within typical bounds",
                )
            )
        else:
            findings.append(
                SanityFinding(
                    rule="PPA",
                    severity="yellow",
                    message=f"PPA {ppa:.2f} is unusual — verify treatment type",
                    raw_value=ppa,
                )
            )
    return findings


# ── Rule 2: Choke Sizing Transcription Normalization ─────────────────────────


def check_choke(choke_size_inches_input: float | None) -> list[SanityFinding]:
    findings: list[SanityFinding] = []

    if choke_size_inches_input is None:
        return findings

    if choke_size_inches_input < 2.0:
        findings.append(
            SanityFinding(
                rule="Choke64ths",
                severity="green",
                message=f"Choke {choke_size_inches_input:.3f} in. within normal range",
            )
        )
        return findings

    # Raw value >= 2.0 — likely N/64" transcribed as whole number
    normalized = choke_size_inches_input / 64.0

    if normalized <= 2.0:
        findings.append(
            SanityFinding(
                rule="Choke64ths",
                severity="yellow",
                message=f"Transcription normalized: {choke_size_inches_input} → {normalized:.3f} in. ({choke_size_inches_input:.0f}/64 in.)",
                raw_value=choke_size_inches_input,
                corrected_value=normalized,
                corrected_unit="in",
            )
        )
    else:
        findings.append(
            SanityFinding(
                rule="Choke64ths",
                severity="red",
                message=f"Confirmed choke {normalized:.3f} in. > 2.0 in. — operational anomaly",
                raw_value=choke_size_inches_input,
                corrected_value=normalized,
                corrected_unit="in",
            )
        )
    return findings


# ── Rule 3: Treating Pressure & Fracture Gradient ────────────────────────────


def check_treating_pressure(
    surface_pressure_psi: float | None,
    tvd_ft: float | None,
    fluid_sg: float | None = None,
    foam_quality_pct: float | None = None,
) -> list[SanityFinding]:
    findings: list[SanityFinding] = []

    if surface_pressure_psi is None or tvd_ft is None or tvd_ft <= 0:
        return findings

    # Dynamic hydrostatic density correction for foam using downhole gas density
    if foam_quality_pct is not None and foam_quality_pct > 0:
        q = foam_quality_pct / 100.0
        rho_liquid_ppg = fluid_sg * 8.33 if fluid_sg else 8.33
        try:
            from mt_oil.domain.gas import downhole_gas_density_ppg, hall_yarborough_z

            # Estimate BHP for gas density; use the surface pressure + liquid hydrostatic
            bhp_est = surface_pressure_psi + 0.433 * rho_liquid_ppg / 8.33 * tvd_ft
            # Approximate reservoir temp (0.016°F/ft + 60°F surface)
            temp_rankine = tvd_ft * 0.016 + 520
            z = hall_yarborough_z(bhp_est, temp_rankine, 0.65)
            rho_gas_ppg = downhole_gas_density_ppg(bhp_est, z, temp_rankine, 0.65)
        except Exception:
            rho_gas_ppg = 0.075
        rho_foam_ppg = (rho_liquid_ppg * (1 - q)) + (rho_gas_ppg * q)
        hydrostatic_psi = 0.052 * rho_foam_ppg * tvd_ft
        density_note = (
            f" (dynamic foam ρ={rho_foam_ppg:.2f} ppg, ρ_gas={rho_gas_ppg:.3f} ppg)"
        )
    else:
        sg = fluid_sg if fluid_sg else 1.0
        hydrostatic_psi = 0.433 * sg * tvd_ft
        density_note = ""

    bhp = surface_pressure_psi + hydrostatic_psi
    fracture_gradient = bhp / tvd_ft

    if surface_pressure_psi > 15000:
        findings.append(
            SanityFinding(
                rule="TreatingPressure",
                severity="red",
                message=f"Surface treating pressure {surface_pressure_psi:,.0f} psi exceeds 15,000 psi burst threshold{density_note}",
                raw_value=surface_pressure_psi,
            )
        )

    if fracture_gradient < 0.55:
        findings.append(
            SanityFinding(
                rule="TreatingPressure",
                severity="red",
                message=f"Apparent fracture gradient {fracture_gradient:.3f} psi/ft < 0.55 — sub-fracture (under-hydrostatic){density_note}",
                raw_value=fracture_gradient,
            )
        )
    elif fracture_gradient > 1.15:
        findings.append(
            SanityFinding(
                rule="TreatingPressure",
                severity="red",
                message=f"Apparent fracture gradient {fracture_gradient:.3f} psi/ft > 1.15 — implausible for non-complex tectonic regime{density_note}",
                raw_value=fracture_gradient,
            )
        )
    else:
        findings.append(
            SanityFinding(
                rule="TreatingPressure",
                severity="green",
                message=f"BHP ~ {bhp:,.0f} psi, FG = {fracture_gradient:.3f} psi/ft within bounds{density_note}",
            )
        )

    return findings


# ── Rule 4: Acid Volume Scaling ──────────────────────────────────────────────


def check_acid_volume(
    acid_volume_gal: float | None,
    total_carrier_volume_gal: float | None,
    net_perforated_ft: float | None = None,
    is_carbonate: bool = False,
) -> list[SanityFinding]:
    findings: list[SanityFinding] = []

    if acid_volume_gal is None or acid_volume_gal <= 0:
        return findings

    if (
        total_carrier_volume_gal is not None
        and total_carrier_volume_gal > 0
        and acid_volume_gal > total_carrier_volume_gal
    ):
        findings.append(
            SanityFinding(
                rule="AcidScaling",
                severity="red",
                message=f"Acid volume ({acid_volume_gal:,.0f} gal) exceeds total carrier fluid ({total_carrier_volume_gal:,.0f} gal)",
                raw_value=acid_volume_gal,
            )
        )

    if net_perforated_ft is not None and net_perforated_ft > 0:
        intensity = acid_volume_gal / net_perforated_ft

        if is_carbonate:
            if intensity < 5:
                findings.append(
                    SanityFinding(
                        rule="AcidScaling",
                        severity="red",
                        message=f"Acid intensity {intensity:.0f} gal/ft < 5 — ineffective coverage on carbonate",
                        raw_value=intensity,
                    )
                )
            elif intensity > 1500:
                findings.append(
                    SanityFinding(
                        rule="AcidScaling",
                        severity="red",
                        message=f"Acid intensity {intensity:,.0f} gal/ft > 1,500 — probable transcription/unit error",
                        raw_value=intensity,
                    )
                )
            elif 300 <= intensity <= 1000:
                findings.append(
                    SanityFinding(
                        rule="AcidScaling",
                        severity="green",
                        message=f"Acid intensity {intensity:.0f} gal/ft in acid frac range (300–1,000+)",
                    )
                )
            elif 50 <= intensity < 300:
                findings.append(
                    SanityFinding(
                        rule="AcidScaling",
                        severity="green",
                        message=f"Acid intensity {intensity:.0f} gal/ft in matrix acidizing range (50–300)",
                    )
                )
            elif 10 <= intensity < 50:
                findings.append(
                    SanityFinding(
                        rule="AcidScaling",
                        severity="green",
                        message=f"Acid intensity {intensity:.0f} gal/ft in wellbore cleanup range (10–50)",
                    )
                )
            else:
                findings.append(
                    SanityFinding(
                        rule="AcidScaling",
                        severity="yellow",
                        message=f"Acid intensity {intensity:.0f} gal/ft outside nominal bands — verify treatment type",
                        raw_value=intensity,
                    )
                )
        else:
            if intensity > 500:
                findings.append(
                    SanityFinding(
                        rule="AcidScaling",
                        severity="yellow",
                        message=f"Acid intensity {intensity:.0f} gal/ft high for non-carbonate — verify",
                        raw_value=intensity,
                    )
                )

    return findings


# ── Rule 5: Acid Intensity per Foot ─────────────────────────────────────────


def check_acid_intensity(
    acid_volume_gal: float | None,
    net_perforated_ft: float | None,
) -> list[SanityFinding]:
    findings: list[SanityFinding] = []

    if acid_volume_gal is None or net_perforated_ft is None or net_perforated_ft <= 0:
        return findings

    intensity = acid_volume_gal / net_perforated_ft

    if intensity < 5:
        findings.append(
            SanityFinding(
                rule="AcidIntensity",
                severity="red",
                message=f"Acid intensity {intensity:.0f} gal/ft < 5 — ineffective coverage",
                raw_value=intensity,
            )
        )
    elif intensity > 1500:
        findings.append(
            SanityFinding(
                rule="AcidIntensity",
                severity="red",
                message=f"Acid intensity {intensity:,.0f} gal/ft > 1,500 — probable transcription/unit error",
                raw_value=intensity,
            )
        )
    elif 300 <= intensity <= 1000:
        findings.append(
            SanityFinding(
                rule="AcidIntensity",
                severity="green",
                message=f"Acid intensity {intensity:.0f} gal/ft in acid frac range (300–1,000+))",
            )
        )
    elif 50 <= intensity < 300:
        findings.append(
            SanityFinding(
                rule="AcidIntensity",
                severity="green",
                message=f"Acid intensity {intensity:.0f} gal/ft in matrix acidizing range (50–300)",
            )
        )
    elif 10 <= intensity < 50:
        findings.append(
            SanityFinding(
                rule="AcidIntensity",
                severity="green",
                message=f"Acid intensity {intensity:.0f} gal/ft in wellbore cleanup range (10–50)",
            )
        )
    else:
        findings.append(
            SanityFinding(
                rule="AcidIntensity",
                severity="yellow",
                message=f"Acid intensity {intensity:.0f} gal/ft outside nominal bands — verify",
                raw_value=intensity,
            )
        )

    return findings


# ── Rule 6: Matrix vs. Frac Pressure / Rate Bounds ──────────────────────────


def check_matrix_validation(
    treatment_class: str | None,
    max_treating_rate_bpm: float | None,
    surface_pressure_psi: float | None,
    fracture_gradient_psi_per_ft: float | None,
    tvd_ft: float | None,
    fluid_sg: float | None = None,
) -> list[SanityFinding]:
    findings: list[SanityFinding] = []

    if treatment_class != "matrix_acidizing":
        return findings

    # Injection rate bounds: matrix limits are ~3–5 bpm; above indicates fracture
    if max_treating_rate_bpm is not None and max_treating_rate_bpm > 5:
        findings.append(
            SanityFinding(
                rule="MatrixValidation",
                severity="red",
                message=f"Misclassified Matrix: injection rate {max_treating_rate_bpm:.1f} bpm exceeds matrix limit (3–5 bpm) — hydraulic fracturing occurred",
                raw_value=max_treating_rate_bpm,
            )
        )

    # Pressure must stay below breakdown:
    #   P_surface < (FG × TVD) − P_hydrostatic
    if (
        surface_pressure_psi is not None
        and fracture_gradient_psi_per_ft is not None
        and tvd_ft is not None
    ):
        breakdown_pressure = fracture_gradient_psi_per_ft * tvd_ft
        sg = fluid_sg if fluid_sg else 1.0
        hydrostatic = 0.433 * sg * tvd_ft
        max_matrix_pressure = breakdown_pressure - hydrostatic
        if surface_pressure_psi >= max_matrix_pressure * 0.9:
            findings.append(
                SanityFinding(
                    rule="MatrixValidation",
                    severity="red",
                    message=f"Misclassified Matrix: treating pressure {surface_pressure_psi:,.0f} psi ≥ matrix max {max_matrix_pressure:,.0f} psi — fracture occurred",
                    raw_value=surface_pressure_psi,
                )
            )

    if not findings:
        findings.append(
            SanityFinding(
                rule="MatrixValidation",
                severity="green",
                message="Matrix acidizing rate & pressure within matrix limits",
            )
        )

    return findings


# ── Rule 7: Gas-to-Liquid Ratio (GLR) ──────────────────────────────────────


def check_glr(
    gas_volume_scf: float | None,
    liquid_volume_bbl: float | None,
):
    findings: list[SanityFinding] = []

    if gas_volume_scf is None or liquid_volume_bbl is None or liquid_volume_bbl <= 0:
        return findings

    if gas_volume_scf <= 0:
        return findings

    glr = gas_volume_scf / liquid_volume_bbl

    if glr < 100:
        findings.append(
            SanityFinding(
                rule="GLR",
                severity="red",
                message=f"GLR {glr:.0f} SCF/bbl < 100 — negligible energization, possible reporting error",
                raw_value=glr,
            )
        )
    elif glr > 5000:
        findings.append(
            SanityFinding(
                rule="GLR",
                severity="red",
                message=f"GLR {glr:,.0f} SCF/bbl > 5,000 — extreme foam instability / erosion risk on high-sand stages",
                raw_value=glr,
            )
        )
    else:
        findings.append(
            SanityFinding(
                rule="GLR",
                severity="green",
                message=f"GLR {glr:,.0f} SCF/bbl within nominal bounds",
            )
        )

    return findings


# ── Rule 8: Foam Quality Classification ─────────────────────────────────────


def check_foam_quality(foam_quality_pct: float | None) -> list[SanityFinding]:
    findings: list[SanityFinding] = []

    if foam_quality_pct is None:
        return findings

    if foam_quality_pct < 0 or foam_quality_pct > 100:
        findings.append(
            SanityFinding(
                rule="FoamQuality",
                severity="red",
                message=f"Foam quality {foam_quality_pct:.1f}% outside 0–100% — unit/data error",
                raw_value=foam_quality_pct,
            )
        )
    elif foam_quality_pct > 80:
        findings.append(
            SanityFinding(
                rule="FoamQuality",
                severity="green",
                message=f"Foam quality {foam_quality_pct:.0f}% → mist / gas frac regime",
            )
        )
    elif foam_quality_pct >= 50:
        findings.append(
            SanityFinding(
                rule="FoamQuality",
                severity="green",
                message=f"Foam quality {foam_quality_pct:.0f}% → stable foam frac",
            )
        )
    elif foam_quality_pct >= 30:
        findings.append(
            SanityFinding(
                rule="FoamQuality",
                severity="green",
                message=f"Foam quality {foam_quality_pct:.0f}% → energized fluid (fluid-assist flowback)",
            )
        )
    else:
        findings.append(
            SanityFinding(
                rule="FoamQuality",
                severity="yellow",
                message=f"Foam quality {foam_quality_pct:.0f}% very low — may not be a true foam treatment",
                raw_value=foam_quality_pct,
            )
        )

    return findings


# ── Composite ────────────────────────────────────────────────────────────────


def run_all_sanity_checks(
    proppant_lbs: float | None = None,
    clean_water_gal: float | None = None,
    choke_inches: float | None = None,
    surface_pressure_psi: float | None = None,
    tvd_ft: float | None = None,
    acid_volume_gal: float | None = None,
    total_carrier_volume_gal: float | None = None,
    net_perforated_ft: float | None = None,
    is_carbonate: bool = False,
    treatment_class: str | None = None,
    is_foam: bool = False,
    foam_quality_pct: float | None = None,
    fluid_sg: float | None = None,
    fracture_gradient_psi_per_ft: float | None = None,
    gas_volume_scf: float | None = None,
    liquid_volume_bbl: float | None = None,
    max_treating_rate_bpm: float | None = None,
) -> list[SanityFinding]:
    findings: list[SanityFinding] = []

    findings.extend(
        check_ppa(
            proppant_lbs,
            clean_water_gal,
            treatment_class=treatment_class,
            is_foam=is_foam,
            foam_quality_pct=foam_quality_pct,
        )
    )
    findings.extend(check_choke(choke_inches))
    findings.extend(
        check_treating_pressure(
            surface_pressure_psi,
            tvd_ft,
            fluid_sg=fluid_sg,
            foam_quality_pct=foam_quality_pct,
        )
    )
    findings.extend(
        check_acid_volume(
            acid_volume_gal,
            total_carrier_volume_gal,
            net_perforated_ft=net_perforated_ft,
            is_carbonate=is_carbonate,
        )
    )
    findings.extend(check_acid_intensity(acid_volume_gal, net_perforated_ft))
    findings.extend(
        check_matrix_validation(
            treatment_class,
            max_treating_rate_bpm,
            surface_pressure_psi,
            fracture_gradient_psi_per_ft,
            tvd_ft,
            fluid_sg=fluid_sg,
        )
    )
    findings.extend(check_glr(gas_volume_scf, liquid_volume_bbl))
    findings.extend(check_foam_quality(foam_quality_pct))

    return findings


def compute_badge(findings: list[SanityFinding]) -> str:
    severity_order = {"green": 0, "yellow": 1, "red": 2}
    worst = "green"
    for f in findings:
        if severity_order.get(f.severity, 0) > severity_order.get(worst, 0):
            worst = f.severity
    return worst
