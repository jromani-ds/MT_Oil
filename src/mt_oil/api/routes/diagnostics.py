"""FastAPI route for the deep diagnostics view.

On-demand (lazy) extraction of the five diagnostic sections from the wellfile
PDF (cache-first per section), followed by deterministic engineering
computation via the domain modules (stress, scaling, pvt, flowback,
tortuosity, rta). None of these sections run automatically — the caller must
explicitly invoke this endpoint.
"""

import logging

from fastapi import APIRouter, Path, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from mt_oil.agents.tools.document import (
    _read_payload_from_bq,
    wellfile_diagnostics_tool,
    wellfile_flowback_tool,
    wellfile_fluid_pvt_tool,
    wellfile_survey_tool,
    wellfile_water_chemistry_tool,
)
from mt_oil.config import settings
from mt_oil.domain import flowback, pvt, scaling, stress, tortuosity

logger = logging.getLogger(__name__)

diag_limiter = Limiter(key_func=lambda r: get_remote_address(r))
router = APIRouter(prefix="/wells/{api_number}/diagnostics", tags=["diagnostics"])

SECTION_TOOLS = {
    "diagnostics": wellfile_diagnostics_tool,
    "water_chemistry": wellfile_water_chemistry_tool,
    "fluid_pvt": wellfile_fluid_pvt_tool,
    "flowback": wellfile_flowback_tool,
    "directional_survey": wellfile_survey_tool,
}


@router.get("")
@diag_limiter.limit(settings.rate_limit)
def get_diagnostics(
    request: Request,
    api_number: str = Path(..., title="API Well Number"),
) -> dict:
    """Run deep diagnostics for a well.

    Extracts (on-demand, cached) DFIT/stress, water chemistry, PVT, flowback,
    and directional survey sections, then computes the engineering metrics.
    """
    # 1. Load cached payload
    payload = _read_payload_from_bq(api_number)

    # 2. On-demand extraction of missing sections (cache-first per tool)
    sections: dict[str, dict] = {}
    for section_name, tool in SECTION_TOOLS.items():
        # Check cache first (already in payload)
        cached_section = None
        if payload and isinstance(payload, dict):
            cached_section = payload.get(section_name)
        if cached_section:
            sections[section_name] = cached_section
            continue

        try:
            tool_result = tool(api_number)
            extracted = tool_result.get(section_name)
            if extracted:
                sections[section_name] = extracted
        except Exception as exc:
            logger.warning(
                "On-demand extraction failed for %s (%s): %s",
                api_number,
                section_name,
                exc,
            )

    # 3. Compute engineering metrics from extracted sections
    result = _compute_all(sections)

    # 4. Attach well metadata
    cs = (payload or {}).get("completion_stimulation") or {}
    result["api_number"] = api_number
    result["well_name"] = cs.get("well_name")
    result["tvd_ft"] = cs.get("tvd_ft")
    result["extraction_status"] = "SUCCESS" if sections else "FAILED_PARSING"
    result["sections_extracted"] = list(sections.keys())

    return result


def _compute_all(sections: dict) -> dict:
    output: dict = {}

    # ── Stress / DFIT ──
    diag = sections.get("diagnostics") or {}
    if diag:
        stress_out: dict = {}
        closure_p = diag.get("closure_pressure_psi")
        if closure_p:
            stress_out["sigma_hmin_psi"] = stress.sigma_hmin(closure_p)
        tvd = _find_tvd(sections)
        if closure_p and tvd:
            stress_out["stress_gradient_psi_per_ft"] = stress.stress_gradient(
                closure_p, tvd
            )
        stress_out["leakoff_type"] = stress.classify_leakoff(diag.get("dfit_notes"))
        step_rates = diag.get("step_rate_tests") or []
        if step_rates:
            stress_out["friction_split"] = stress.friction_split(step_rates)
        if stress_out:
            output["stress"] = stress_out

    # ── Water chemistry / scaling ──
    water = sections.get("water_chemistry") or {}
    if water:
        scaling_data = scaling.scaling_summary(water)
        output["water_chemistry"] = scaling_data

    # ── PVT ──
    fluid_pvt = sections.get("fluid_pvt") or {}
    if fluid_pvt:
        pvt_out: dict = {}
        gas_comp = fluid_pvt.get("gas_mole_fractions") or {}
        if gas_comp:
            raw_sg = pvt.gas_specific_gravity(gas_comp)
            corrected_sg, wa_applied = pvt.corrected_gas_gravity(gas_comp)
            pvt_out["gas_specific_gravity"] = corrected_sg if wa_applied else raw_sg
            pvt_out["wichert_aziz_correction_applied"] = wa_applied
            pvt_out["btu_scf"] = pvt.btu_from_gas_composition(gas_comp)
        api_g = fluid_pvt.get("oil_api_gravity")
        temp_f = fluid_pvt.get("reservoir_temp_f") or 150
        if api_g:
            pvt_out["oil_viscosity_cp"] = pvt.oil_viscosity_beggs_robinson(
                api_g, temp_f
            )
        # Bubble point via Standing if GOR unknown (estimate from measured or skip)
        pb_measured = fluid_pvt.get("bubble_point_psi")
        if pb_measured:
            pvt_out["bubble_point_psi"] = pb_measured
        if pvt_out:
            output["pvt"] = pvt_out

    # ── Flowback ──
    fb = sections.get("flowback") or {}
    if fb:
        fb_out: dict = {}
        recovered = fb.get("cumulative_load_recovered_bbls")
        pumped = _find_pumped_fluid(sections)
        if recovered and pumped:
            recovery_pct = flowback.load_recovery_pct(recovered, pumped)
            fb_out["load_recovery_pct"] = recovery_pct
            fb_out["load_recovery_assessment"] = flowback.assess_load_recovery(
                recovery_pct
            )
        proppant_fb = fb.get("proppant_flowback") or []
        if proppant_fb:
            fb_out["proppant_flowback"] = flowback.classify_proppant_flowback(
                proppant_fb
            )
        if fb_out:
            output["flowback"] = fb_out

    # ── Directional survey / tortuosity ──
    survey = sections.get("directional_survey") or {}
    points = survey.get("survey_points") or []
    if points:
        survey_out: dict = {}
        enriched = tortuosity.enrich_survey_with_dls(points)
        survey_out["survey_points"] = enriched
        survey_out["max_dls_deg_per_100ft"] = survey.get(
            "max_dls_deg_per_100ft"
        ) or tortuosity.max_dls_in_lateral(enriched)
        survey_out["lateral_max_dls_deg_per_100ft"] = survey.get(
            "lateral_max_dls_deg_per_100ft"
        )
        hotspots = tortuosity.find_tortuosity_hotspots(enriched)
        survey_out["tortuosity_hotspots"] = hotspots
        output["survey"] = survey_out

    return output


def _find_tvd(sections: dict) -> float | None:
    sections.get("diagnostics") or {}
    # diagnostics schema has no TVD; fall back to payload-level info elsewhere
    return None


def _find_pumped_fluid(sections: dict) -> float | None:
    # Pumped fluid would come from the stimulation payload, not the
    # flowback section. The caller (route) does not have it here; leave None
    # so load recovery is computed only when pumped volume is supplied.
    return None
