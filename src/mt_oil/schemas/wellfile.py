"""Pydantic schemas for wellfile agent extraction and API responses."""

from typing import Optional

from pydantic import BaseModel, Field


class CompletionSpecs(BaseModel):
    api_number: str = Field(description="10 or 14 digit API identifier")
    well_name: Optional[str] = Field(None, description="Official well name and number")
    tvd_ft: Optional[float] = Field(None, description="True Vertical Depth in feet")
    md_ft: Optional[float] = Field(None, description="Total Measured Depth in feet")
    lateral_length_ft: Optional[float] = Field(
        None, description="Horizontal lateral length in feet"
    )
    total_clean_fluid_bbls: Optional[float] = Field(
        None, description="Total clean fracturing fluid in barrels"
    )
    total_proppant_lbs: Optional[float] = Field(
        None, description="Total proppant/sand weight in pounds"
    )
    max_treating_pressure_psi: Optional[float] = Field(
        None, description="Maximum treating pressure in PSI"
    )
    casing_intermediate_depth_ft: Optional[float] = Field(
        None, description="Intermediate casing setting depth in feet"
    )


class WellfileExtraction(BaseModel):
    api_number: str
    specs: Optional[CompletionSpecs] = None
    extraction_status: str = Field(description="SUCCESS or FAILED_PARSING")
    cache_hit: bool = Field(
        default=False, description="Whether the result came from BigQuery cache"
    )


class ProductionSummary(BaseModel):
    total_months: int = Field(
        default=0, description="Number of months of production history"
    )
    peak_oil_bbls: float = Field(default=0, description="Peak monthly oil production")
    peak_gas_mcf: float = Field(default=0, description="Peak monthly gas production")
    eur_boe: Optional[float] = Field(
        None, description="Estimated ultimate recovery in BOE"
    )
    dca_method: Optional[str] = Field(None, description="Best-fit DCA method")


class WellfileAgentResponse(BaseModel):
    api_number: str
    extraction_status: str = Field(description="SUCCESS or FAILED_PARSING")
    cache_hit: bool = Field(default=False)
    completion_specs: Optional[CompletionSpecs] = None
    production_summary: Optional[ProductionSummary] = None
    proppant_intensity_lbs_per_ft: Optional[float] = Field(
        None, description="Proppant intensity (lbs proppant / ft lateral)"
    )
    fluid_intensity_bbls_per_ft: Optional[float] = Field(
        None, description="Fluid intensity (bbls fluid / ft lateral)"
    )
    well_name: Optional[str] = Field(
        None, description="Official well name (mirrored from specs for convenience)"
    )


class WellfileAgentRequest(BaseModel):
    api_number: str = Field(description="API well number to analyze")
