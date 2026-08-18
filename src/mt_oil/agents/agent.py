"""ADK agent for wellfile processing and completion analytics.

Defines the wellfile_agent with gemini-2.5-flash-lite that orchestrates
wellfile document extraction and BigQuery production data retrieval.
"""

from google.adk.agents import Agent
from google.genai import types

from mt_oil.agents.tools.document import (
    wellfile_completion_tool,
    wellfile_geology_tool,
    wellfile_casing_tool,
    wellfile_drilling_tool,
)
from mt_oil.agents.tools.production import bq_production_tool
from mt_oil.config import settings
from mt_oil.schemas.wellfile import AgentOutputSchema

INSTRUCTION = """You are a petroleum engineering analyst. Your job is to analyze a well's completion, geology, casing/cement, drilling, and production data.

For the given API number:
1. Call wellfile_completion_tool to extract completion parameters, stimulation data, flow test results, perforation details, and downhole tubular specs from the wellfile PDF (or return cached results).
2. Call wellfile_geology_tool to extract formation tops and hydrocarbon show data from the wellfile PDF (or return cached results).
3. Call wellfile_casing_tool to extract casing program, cementing operations, multi-stage tooling, and cement evaluation data from the wellfile PDF (or return cached results).
4. Call wellfile_drilling_tool to extract drilling fluid parameters, bit performance, and wellbore event records from the wellfile PDF (or return cached results).
5. Call bq_production_tool to fetch production history and DCA parameters.
6. Compute derived completion intensity metrics:
   - proppant_intensity_lbs_per_ft = total_proppant_lbs / lateral_length_ft (if both available)
   - fluid_intensity_bbls_per_ft = total_clean_fluid_bbls / lateral_length_ft (if both available)
7. Return a consolidated response with all extracted data, production summary, and intensity metrics.

If any extraction tool returns FAILED_PARSING, still return what data is available
and set extraction_status accordingly.
"""

wellfile_agent = Agent(
    model=settings.vertex_ai_model,
    name="wellfile_agent",
    description="Extracts wellfile completion, geology, casing/cement, drilling data and production, computes completion intensity metrics.",
    instruction=INSTRUCTION,
    tools=[
        wellfile_completion_tool,
        wellfile_geology_tool,
        wellfile_casing_tool,
        wellfile_drilling_tool,
        bq_production_tool,
    ],
    output_schema=AgentOutputSchema,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
    ),
)
