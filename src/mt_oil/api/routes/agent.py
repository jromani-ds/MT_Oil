"""FastAPI route for the wellfile agent endpoint."""

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from slowapi import Limiter
from slowapi.util import get_remote_address

from mt_oil.agents.agent import wellfile_agent
from mt_oil.agents.tools.document import _check_bq_cache
from mt_oil.schemas.wellfile import (
    CompletionSpecs,
    ProductionSummary,
    WellfileAgentRequest,
    WellfileAgentResponse,
)

logger = logging.getLogger(__name__)

agent_limiter = Limiter(key_func=lambda r: get_remote_address(r))

router = APIRouter(prefix="/agent", tags=["agent"])

_session_service = InMemorySessionService()
_runner = Runner(
    agent=wellfile_agent,
    app_name="wellfile_agent",
    session_service=_session_service,
)


def _compute_intensity(
    completion: dict | None,
) -> tuple[float | None, float | None]:
    if not completion:
        return None, None
    lateral = completion.get("lateral_length_ft")
    proppant = completion.get("total_proppant_lbs")
    fluid = completion.get("total_clean_fluid_bbls")
    proppant_int = None
    fluid_int = None
    if lateral and lateral > 0:
        if proppant:
            proppant_int = round(proppant / lateral, 2)
        if fluid:
            fluid_int = round(fluid / lateral, 2)
    return proppant_int, fluid_int


@router.post("/wellfile", response_model=WellfileAgentResponse)
async def process_wellfile(request: Request, body: WellfileAgentRequest):
    """Analyze a wellfile: extract completion specs, fetch production, compute intensity metrics."""
    api_number = body.api_number

    # Pre-agent cache check — bypasses LLM entirely on cache hit
    cached = _check_bq_cache(api_number)
    if cached is not None:
        completion = CompletionSpecs(
            api_number=api_number,
            well_name=cached.get("well_name"),
            tvd_ft=cached.get("tvd_ft"),
            md_ft=cached.get("md_ft"),
            lateral_length_ft=cached.get("lateral_length_ft"),
            total_clean_fluid_bbls=cached.get("total_clean_fluid_bbls"),
            total_proppant_lbs=cached.get("total_proppant_lbs"),
            max_treating_pressure_psi=cached.get("max_treating_pressure_psi"),
            casing_intermediate_depth_ft=cached.get("casing_intermediate_depth_ft"),
        )
        proppant_int, fluid_int = _compute_intensity(completion.model_dump())
        return WellfileAgentResponse(
            api_number=api_number,
            extraction_status="SUCCESS",
            cache_hit=True,
            completion_specs=completion,
            proppant_intensity_lbs_per_ft=proppant_int,
            fluid_intensity_bbls_per_ft=fluid_int,
        )

    # Cache miss: invoke the ADK agent
    user_content = types.Content(
        role="user",
        parts=[types.Part(text=f"Analyze wellfile data for API number {api_number}")],
    )

    session = _session_service.create_session(
        app_name="wellfile_agent",
        user_id="api",
    )

    final_text = ""
    async for event in _runner.run_async(
        user_id="api",
        session_id=session.id,
        new_message=user_content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_text += part.text

    if not final_text:
        raise HTTPException(status_code=500, detail="Agent returned no response")

    result = _parse_agent_response(api_number, final_text)
    return result


def _parse_agent_response(api_number: str, text: str) -> WellfileAgentResponse:
    """Parse the ADK agent's JSON response into a WellfileAgentResponse."""
    try:
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Agent returned invalid JSON for %s", api_number)
        return WellfileAgentResponse(
            api_number=api_number,
            extraction_status="FAILED_PARSING",
            cache_hit=False,
        )

    specs_data = (
        data.get("completion_specs") or data.get("completion_parameters") or data
    )
    try:
        completion = CompletionSpecs(**specs_data) if specs_data else None
    except Exception as exc:
        logger.warning("Failed to parse completion specs: %s", exc)
        completion = None

    prod_data = data.get("production_summary") or data.get("production_data") or {}
    production_summary = ProductionSummary(
        total_months=prod_data.get("total_months", 0),
        peak_oil_bbls=prod_data.get("peak_oil_bbls", 0),
        peak_gas_mcf=prod_data.get("peak_gas_mcf", 0),
        eur_boe=prod_data.get("eur_boe"),
        dca_method=prod_data.get("dca_method"),
    )

    extraction_status = data.get("extraction_status", "SUCCESS")
    cache_hit = data.get("cache_hit", False)

    specs_dict = completion.model_dump() if completion else {}
    proppant_int, fluid_int = _compute_intensity(specs_dict)

    return WellfileAgentResponse(
        api_number=api_number,
        extraction_status=extraction_status,
        cache_hit=cache_hit,
        completion_specs=completion,
        production_summary=production_summary,
        proppant_intensity_lbs_per_ft=proppant_int,
        fluid_intensity_bbls_per_ft=fluid_int,
        well_name=specs_dict.get("well_name"),
    )
