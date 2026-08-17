"""Reconciliation engine — gap-fill, variance, arbitration between State and FracFocus."""

import math

from mt_oil.fracfocus.schemas import (
    FracFocusWellAggregate,
)
from mt_oil.fracfocus.units import gal_to_bbl, to_clean_water_equivalent
from mt_oil.reconciliation.schemas import (
    ProvenanceTag,
    ReconciledStimulation,
    SourceView,
    VarianceReport,
)
from mt_oil.sanity.sanity_check import compute_badge, run_all_sanity_checks

BLANK_VALUES = {None, "", "N/A", "n/a", "na", "NA", "acidized/fraced", "fraced"}


def _is_blank(val) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        return val.strip().lower() in {
            x.lower() for x in BLANK_VALUES if isinstance(x, str)
        }
    try:
        return math.isnan(val)
    except TypeError:
        return False


def _variance_pct(state_val: float | None, ff_val: float | None) -> float | None:
    if state_val is None or ff_val is None or state_val == 0:
        return None
    return abs(state_val - ff_val) / abs(state_val) * 100.0


def _compute_net_perforated_ft(perforations: list[dict]) -> float:
    total = 0.0
    for p in perforations:
        top = p.get("top_md_ft")
        bottom = p.get("bottom_md_ft")
        status = p.get("status", "").lower()
        if top is not None and bottom is not None and status in ("open", "", None):
            length = bottom - top
            if length > 0:
                total += length
    return total


def reconcile(
    api_number: str,
    state_payload: dict | None,
    ff_aggregate: FracFocusWellAggregate | None,
    is_carbonate: bool = False,
) -> ReconciledStimulation:
    result = ReconciledStimulation(api_number=api_number)

    # ── Extract state values ──
    cs = {}
    ip_flow = {}
    perforations: list[dict] = []
    stimulation_stages: list[dict] = []
    if state_payload:
        cs = state_payload.get("completion_stimulation") or {}
        ip_flow = cs.get("ip_flow_test") or {}
        perforations = cs.get("perforations") or []
        stimulation_stages = cs.get("stimulation_stages") or []

    state_fluid_bbls = cs.get("total_clean_fluid_bbls")
    state_proppant_lbs = cs.get("total_proppant_lbs")
    state_treating_pressure = cs.get("max_treating_pressure_psi")
    state_tvd = cs.get("tvd_ft")
    state_well_name = cs.get("well_name")

    choke = ip_flow.get("choke_size_inches")
    ip_flow.get("flowing_tubing_pressure_psi")
    ip_flow.get("shut_in_tubing_pressure_psi")

    # Stage-level fluid sums
    state_stage_fluid_bbls = (
        sum(s.get("fluid_volume_bbls") or 0 for s in stimulation_stages)
        if stimulation_stages
        else None
    )

    cs.get("total_proppant_lbs")
    state_stage_max_pressure = (
        max(
            (s.get("max_treating_pressure_psi") or 0 for s in stimulation_stages),
            default=None,
        )
        if stimulation_stages
        else None
    )

    # ── Extract FracFocus values ──
    ff_fluid_bbls = None
    ff_fluid_cwe_bbls = None
    ff_proppant_lbs = None
    ff_acid_gal = None
    ff_tvd = None
    ff_proppant_breakdown = None
    ff_additives = None
    ff_gas_components = []

    if ff_aggregate:
        if ff_aggregate.total_water_volume_gal is not None:
            # FracFocus reports base water volume in gallons. Tag it as clean
            # water by default, but also compute the CWE in case the disclosure
            # actually reflects slurry (sand displacement inflates volume).
            ff_fluid_bbls = gal_to_bbl(ff_aggregate.total_water_volume_gal)
            ff_fluid_cwe_bbls = to_clean_water_equivalent(
                ff_fluid_bbls, ff_aggregate.total_proppant_lbs
            )
        ff_proppant_lbs = ff_aggregate.total_proppant_lbs
        ff_acid_gal = ff_aggregate.total_acid_gal
        ff_tvd = ff_aggregate.tvd_ft
        ff_proppant_breakdown = ff_aggregate.proppant_breakdown
        ff_additives = ff_aggregate.additives
        ff_gas_components = ff_aggregate.gas_components

    # ── Populate source views ──
    result.state_source = SourceView(
        total_clean_fluid_bbls=state_fluid_bbls,
        total_proppant_lbs=state_proppant_lbs,
        max_treating_pressure_psi=state_treating_pressure or state_stage_max_pressure,
        tvd_ft=state_tvd,
        provenance=(
            [
                ProvenanceTag(
                    source="State Filing",
                    field_name="total_clean_fluid_bbls",
                    original_value=state_fluid_bbls,
                    original_unit="bbl",
                    volume_type="clean_water",
                )
            ]
            if state_fluid_bbls is not None
            else []
        ),
    )
    result.fracfocus_source = SourceView(
        total_clean_fluid_bbls=(
            ff_fluid_cwe_bbls if ff_fluid_cwe_bbls is not None else ff_fluid_bbls
        ),
        total_proppant_lbs=ff_proppant_lbs,
        total_acid_gal=ff_acid_gal,
        tvd_ft=ff_tvd,
        provenance=(
            [
                ProvenanceTag(
                    source="FracFocus (Disclosed)",
                    field_name="total_clean_fluid_bbls",
                    original_value=ff_fluid_bbls,
                    original_unit="bbl",
                    volume_type=(
                        "clean_water"
                        if ff_fluid_cwe_bbls is not None
                        and abs(ff_fluid_cwe_bbls - ff_fluid_bbls) < 0.01
                        else "slurry_uncorrected"
                    ),
                )
            ]
            if ff_fluid_bbls is not None
            else []
        ),
    )

    # ── Gap-fill: State missing → fill from FF (using CWE) ──
    provenance_tags: list[ProvenanceTag] = []
    reconciled_fluid = state_fluid_bbls
    reconciled_proppant = state_proppant_lbs
    reconciled_acid = (
        ff_acid_gal  # acid is typically FF-only; state rarely has it explicitly
    )

    if _is_blank(state_fluid_bbls) and ff_fluid_cwe_bbls is not None:
        reconciled_fluid = ff_fluid_cwe_bbls
        provenance_tags.append(
            ProvenanceTag(
                source="FracFocus (Disclosed)",
                field_name="total_clean_fluid_bbls",
                original_value=ff_fluid_cwe_bbls,
                original_unit="bbl",
                volume_type="clean_water",
            )
        )
    elif not _is_blank(state_fluid_bbls) and state_stage_fluid_bbls is not None:
        # Stage-vs-total: compare cumulative stage sum to total
        cumulative_stages = sum(
            s.get("fluid_volume_bbls") or 0 for s in stimulation_stages
        )
        if abs(cumulative_stages - state_fluid_bbls) > 0.01 * state_fluid_bbls:
            result.variance = VarianceReport(
                fluid_volume_delta_pct=_variance_pct(
                    state_fluid_bbls, cumulative_stages
                ),
                status="Discrepancy Detected",
                stage_resolution_note=f"Stage sum ({cumulative_stages:,.0f} bbl) differs from total ({state_fluid_bbls:,.0f} bbl)",
            )

    if _is_blank(state_proppant_lbs) and ff_proppant_lbs is not None:
        reconciled_proppant = ff_proppant_lbs
        provenance_tags.append(
            ProvenanceTag(
                source="FracFocus (Disclosed)",
                field_name="total_proppant_lbs",
                original_value=ff_proppant_lbs,
                original_unit="lbs",
            )
        )

    result.well_name = state_well_name or (
        ff_aggregate.well_name if ff_aggregate else None
    )

    # ── Variance calculation (uses CWE-normalized FF fluid) ──
    if result.variance is None:
        ff_compare_fluid = (
            ff_fluid_cwe_bbls if ff_fluid_cwe_bbls is not None else ff_fluid_bbls
        )
        fluid_var = _variance_pct(state_fluid_bbls, ff_compare_fluid)
        proppant_var = _variance_pct(state_proppant_lbs, ff_proppant_lbs)
        acid_var = _variance_pct(_compute_acid_from_state(cs), ff_acid_gal)

        if fluid_var is not None or proppant_var is not None or acid_var is not None:
            max_var = max(
                v for v in [fluid_var, proppant_var, acid_var] if v is not None
            )
            if max_var <= 10:
                status = "Verified / Harmonized"
                # Harmonize to state values
            else:
                status = "Discrepancy Detected"

            result.variance = VarianceReport(
                fluid_volume_delta_pct=fluid_var,
                proppant_mass_delta_pct=proppant_var,
                acid_volume_delta_pct=acid_var,
                status=status,
            )

    # ── Populate reconciled fields ──
    result.total_clean_fluid_bbls = reconciled_fluid
    result.total_proppant_lbs = reconciled_proppant
    result.total_acid_gal = reconciled_acid
    result.max_treating_pressure_psi = (
        state_treating_pressure or state_stage_max_pressure
    )
    result.net_perforated_ft = _compute_net_perforated_ft(perforations)
    result.proppant_breakdown = ff_proppant_breakdown
    result.additives = ff_additives
    result.gas_components = ff_gas_components

    # Acid intensity
    if (
        result.total_acid_gal
        and result.net_perforated_ft
        and result.net_perforated_ft > 0
    ):
        result.acid_intensity_gal_per_ft = (
            result.total_acid_gal / result.net_perforated_ft
        )

    if ff_aggregate:
        result.base_fluid_type = ff_aggregate.base_fluid_type

    # ── Treatment classification ──
    from mt_oil.sanity.classify import classify_treatment, compute_foam_quality

    # Clean water volume (gal) and liquid volume (bbl) for foam/GLR math
    clean_water_gal = None
    liquid_volume_bbl = None
    if reconciled_fluid is not None:
        clean_water_gal = reconciled_fluid * 42.0
        liquid_volume_bbl = reconciled_fluid

    # Compute foam quality using downhole gas volume (real-gas law)
    liquid_gal = clean_water_gal  # base carrier fluid in gallons
    total_gas_scf = (
        sum((g.volume_scf or 0.0) for g in ff_gas_components)
        if ff_gas_components
        else 0.0
    )

    gas_downhole_gal = None
    if total_gas_scf > 0 and result.max_treating_pressure_psi is not None:
        from mt_oil.domain.gas import bhp_estimate, downhole_gas_volume

        tvd = state_tvd or ff_tvd or 10000
        bhp = bhp_estimate(result.max_treating_pressure_psi, tvd)
        gas_downhole_gal = downhole_gas_volume(
            surface_scf=total_gas_scf,
            p_bhp_psia=bhp,
            t_rankine=tvd * 0.016
            + 520,  # approx reservoir temp: 0.016°F/ft + 60°F surface
            gas_gravity=0.65,
        )

    foam_quality = None
    if (
        gas_downhole_gal is not None
        and gas_downhole_gal > 0
        and liquid_gal is not None
        and liquid_gal > 0
    ):
        foam_quality = compute_foam_quality(gas_downhole_gal, liquid_gal)

    result.foam_quality_pct = foam_quality

    # Gas-to-Liquid Ratio (GLR) in SCF/bbl
    if total_gas_scf > 0 and reconciled_fluid is not None and reconciled_fluid > 0:
        result.glr_scf_per_bbl = total_gas_scf / reconciled_fluid

    t_class, _t_note = classify_treatment(
        has_acid=(ff_acid_gal is not None and ff_acid_gal > 0),
        has_gas=bool(ff_gas_components),
        total_proppant_lbs=reconciled_proppant,
        max_treating_rate_bpm=_compute_max_rate(stimulation_stages),
        max_treating_pressure_psi=result.max_treating_pressure_psi,
        tvd_ft=state_tvd or ff_tvd,
        foam_quality_pct=foam_quality,
        acid_volume_gal=result.total_acid_gal,
        net_perforated_ft=result.net_perforated_ft,
    )
    result.treatment_class = t_class

    # ── Proppant concentration ──
    if reconciled_proppant is not None and clean_water_gal and clean_water_gal > 0:
        result.proppant_concentration_ppa = reconciled_proppant / clean_water_gal

    # ── Sanity checks ──
    is_foam = result.treatment_class in ("foam", "energized", "mist")
    result.sanity_findings = run_all_sanity_checks(
        proppant_lbs=reconciled_proppant,
        clean_water_gal=clean_water_gal,
        choke_inches=choke,
        surface_pressure_psi=result.max_treating_pressure_psi,
        tvd_ft=state_tvd or ff_tvd,
        acid_volume_gal=result.total_acid_gal,
        total_carrier_volume_gal=clean_water_gal,
        net_perforated_ft=result.net_perforated_ft,
        is_carbonate=is_carbonate,
        treatment_class=result.treatment_class,
        is_foam=is_foam,
        foam_quality_pct=result.foam_quality_pct,
        fluid_sg=1.0,
        fracture_gradient_psi_per_ft=_compute_fracture_gradient(
            result.max_treating_pressure_psi, state_tvd or ff_tvd
        ),
        gas_volume_scf=total_gas_scf,
        liquid_volume_bbl=liquid_volume_bbl,
        max_treating_rate_bpm=_compute_max_rate(stimulation_stages),
    )
    result.badge = compute_badge(result.sanity_findings)

    # ── Attach provenance ──
    for tag in provenance_tags:
        if (
            tag.field_name == "total_clean_fluid_bbls"
            or tag.field_name == "total_proppant_lbs"
        ):
            result.state_source.provenance.append(tag)

    return result


def _compute_acid_from_state(cs: dict) -> float | None:
    stages = cs.get("stimulation_stages") or []
    total_acid = 0.0
    has_acid = False
    for s in stages:
        tt = (s.get("treatment_type") or "").lower()
        if "acid" in tt:
            has_acid = True
            fb = s.get("fluid_volume_bbls")
            if fb is not None:
                total_acid += fb
    return total_acid if has_acid else None


def _compute_max_rate(stages: list[dict]) -> float | None:
    rates = [
        s.get("injection_rate_bpm")
        for s in stages
        if s.get("injection_rate_bpm") is not None
    ]
    return max(rates) if rates else None


def _compute_fracture_gradient(
    surface_pressure_psi: float | None, tvd_ft: float | None
) -> float | None:
    if surface_pressure_psi is None or tvd_ft is None or tvd_ft <= 0:
        return None
    hydrostatic = 0.433 * tvd_ft
    bhp = surface_pressure_psi + hydrostatic
    return bhp / tvd_ft
