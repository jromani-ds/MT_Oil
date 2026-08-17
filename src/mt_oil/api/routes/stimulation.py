"""FastAPI route for the reconciled stimulation view.

Exposes unified engineering totals with multi-source reconciliation,
engineering sanity checks, and optional engineer overrides.
"""

import logging

from fastapi import APIRouter, HTTPException, Path, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from mt_oil.agents.tools.document import _read_payload_from_bq
from mt_oil.config import settings
from mt_oil.data.bigquery_loader import BigQueryDataLoader
from mt_oil.reconciliation.schemas import OverrideEntry, ReconciledStimulation
from mt_oil.reconciliation.service import get_reconciled_stimulation

logger = logging.getLogger(__name__)

stim_limiter = Limiter(key_func=lambda r: get_remote_address(r))
router = APIRouter(prefix="/wells/{api_number}/stimulation", tags=["stimulation"])

_bq_loader: BigQueryDataLoader | None = None


def _get_loader() -> BigQueryDataLoader | None:
    global _bq_loader
    if _bq_loader is None and settings.gcp_project_id and settings.bigquery_dataset:
        _bq_loader = BigQueryDataLoader(
            settings.gcp_project_id, settings.bigquery_dataset
        )
    return _bq_loader


@router.get("")
@stim_limiter.limit(settings.rate_limit)
def get_reconciled_view(
    request: Request,
    api_number: str = Path(..., title="API Well Number"),
) -> ReconciledStimulation:
    """Get reconciled stimulation data for a well.

    Combines state wellfile payload and FracFocus disclosures with
    gap-filling, variance arbitration, and engineering sanity checks.
    """
    bq_loader = _get_loader()

    # Load state payload from wellfile cache
    state_payload = None
    try:
        state_payload = _read_payload_from_bq(api_number)
    except Exception as exc:
        logger.warning("Failed to load state payload for %s: %s", api_number, exc)

    try:
        result = get_reconciled_stimulation(
            api_number=api_number,
            state_payload=state_payload,
            bq_loader=bq_loader,
        )
    except Exception as exc:
        logger.exception("Reconciliation failed for %s", api_number)
        raise HTTPException(
            status_code=500,
            detail=f"Reconciliation failed: {exc}",
        )

    return result


@router.post("/override")
@stim_limiter.limit("10/minute")
def set_override(
    request: Request,
    api_number: str = Path(..., title="API Well Number"),
    override: OverrideEntry = ...,
):
    """Set an engineer override for a stimulation parameter.

    Overrides are upserted into the `stimulation_overrides` BigQuery table
    and take highest priority in the reconciled view.
    """
    bq_loader = _get_loader()
    if not bq_loader:
        raise HTTPException(status_code=503, detail="Data source not available")

    try:
        from google.cloud import bigquery

        client = bigquery.Client(project=settings.gcp_project_id)
        import datetime

        table_ref = (
            f"{settings.gcp_project_id}.{settings.bigquery_dataset}"
            ".stimulation_overrides"
        )
        rows = [
            {
                "api_number": api_number,
                "field": override.field,
                "value": override.value,
                "note": override.note,
                "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
            }
        ]
        errors = client.insert_rows_json(table_ref, rows)
        if errors:
            raise HTTPException(
                status_code=500, detail=f"Failed to write override: {errors}"
            )
        return {
            "status": "overridden",
            "api_number": api_number,
            "field": override.field,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Override write failed for %s", api_number)
        raise HTTPException(status_code=500, detail=str(exc))
