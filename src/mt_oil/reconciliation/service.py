"""Reconciliation orchestration service.

Loads state (wellfile payload) and FracFocus (BigQuery aggregate + detail)
then runs the reconciliation engine.
"""

import logging

from mt_oil.data.bigquery_loader import BigQueryDataLoader
from mt_oil.domain.lithology import classify_lithology
from mt_oil.fracfocus.schemas import FracFocusWellAggregate
from mt_oil.reconciliation.engine import reconcile
from mt_oil.reconciliation.schemas import ReconciledStimulation

logger = logging.getLogger(__name__)


def get_reconciled_stimulation(
    api_number: str,
    state_payload: dict | None = None,
    bq_loader: BigQueryDataLoader | None = None,
) -> ReconciledStimulation:
    """Build the reconciled stimulation view for a well.

    Args:
        api_number: 10- or 14-digit API number.
        state_payload: Optional pre-loaded wellfile payload dict.
                       If None, reads state from wellfile_parsed_metadata BQ cache.
        bq_loader: Optional pre-configured BigQueryDataLoader.

    Returns:
        ReconciledStimulation with reconciled values, source views,
        variance report, and sanity findings.
    """
    # ── Load FracFocus aggregate from BigQuery ──
    ff_aggregate: FracFocusWellAggregate | None = None
    if bq_loader:
        try:
            ff_data = bq_loader.load_fracfocus_well(api_number)
            if ff_data:
                ff_aggregate = _dict_to_ff_aggregate(ff_data, api_number)
        except Exception as exc:
            logger.warning("Failed to load FracFocus for %s: %s", api_number, exc)

    # ── Determine if carbonate (for acid sanity checks) ──
    is_carbonate = False
    if state_payload:
        geology = state_payload.get("geology") or {}
        formation_tops = geology.get("formation_tops") or []
        if formation_tops:
            # Use the deepest formation top as the target
            deepest = max(formation_tops, key=lambda t: t.get("tvd_ft", 0) or 0)
            formation_name = deepest.get("formation_name", "")
            if formation_name:
                result = classify_lithology(formation_name)
                is_carbonate = result.is_carbonate

    # ── Run reconciliation ──
    result = reconcile(
        api_number=api_number,
        state_payload=state_payload,
        ff_aggregate=ff_aggregate,
        is_carbonate=is_carbonate,
    )

    return result


def _dict_to_ff_aggregate(data: dict, api_number: str) -> FracFocusWellAggregate:
    """Convert a dict from BQ loader to FracFocusWellAggregate."""
    from mt_oil.fracfocus.schemas import AdditiveProfile, ProppantBreakdown

    proppant_breakdown = None
    raw_pb = data.get("proppant_breakdown")
    if raw_pb and isinstance(raw_pb, dict):
        proppant_breakdown = ProppantBreakdown(**raw_pb)

    additives = None
    raw_add = data.get("additives")
    if raw_add and isinstance(raw_add, dict):
        additives = AdditiveProfile(**raw_add)

    gas_components = data.get("gas_components") or []

    return FracFocusWellAggregate(
        api_wellno=api_number,
        total_water_volume_gal=data.get("total_water_volume_gal"),
        total_nonwater_volume_gal=data.get("total_nonwater_volume_gal"),
        total_proppant_lbs=data.get("total_proppant_lbs"),
        total_acid_gal=data.get("total_acid_gal"),
        proppant_breakdown=proppant_breakdown,
        additives=additives,
        base_fluid_type=data.get("base_fluid_type"),
        gas_components=gas_components,
        tvd_ft=data.get("tvd_ft"),
        job_start_date=data.get("job_start_date"),
        job_end_date=data.get("job_end_date"),
        operator=data.get("operator"),
        well_name=data.get("well_name"),
    )
