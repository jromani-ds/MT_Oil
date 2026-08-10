"""ADK agent for wellfile processing and completion analytics.

Defines the wellfile_agent with gemini-2.5-flash-lite that orchestrates
wellfile document extraction and BigQuery production data retrieval.
"""

from google.adk.agents import Agent
from google.genai import types

from mt_oil.agents.tools.document import wellfile_document_tool
from mt_oil.agents.tools.production import bq_production_tool

INSTRUCTION = """You are a petroleum engineering analyst. Your job is to analyze a well's completion and production data.

For the given API number:
1. Call wellfile_document_tool to extract completion parameters from the wellfile PDF (or get cached results).
2. Call bq_production_tool to fetch production history and DCA parameters.
3. Compute derived completion intensity metrics:
   - proppant_intensity_lbs_per_ft = total_proppant_lbs / lateral_length_ft (if both available)
   - fluid_intensity_bbls_per_ft = total_clean_fluid_bbls / lateral_length_ft (if both available)
4. Return a consolidated response with all completion specs, production summary, and intensity metrics.

If extraction_status is FAILED_PARSING, still return what data is available
and set extraction_status accordingly.
"""

wellfile_agent = Agent(
    model="gemini-2.5-flash-lite",
    name="wellfile_agent",
    description="Extracts wellfile completion parameters and production data, computes completion intensity metrics.",
    instruction=INSTRUCTION,
    tools=[wellfile_document_tool, bq_production_tool],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
    ),
)
