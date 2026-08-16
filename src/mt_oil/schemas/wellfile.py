"""Pydantic schemas for wellfile agent extraction and API responses."""

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Priority 1: Completion, Stimulation, and Production Performance
# ---------------------------------------------------------------------------


class IpFlowTest(BaseModel):
    test_duration_hrs: Optional[float] = Field(
        None, description="Test duration in hours"
    )
    oil_rate_24hr_bbls: Optional[float] = Field(
        None, description="24-hour equivalent oil rate in barrels"
    )
    gas_rate_24hr_mcf: Optional[float] = Field(
        None, description="24-hour equivalent gas rate in MCF"
    )
    water_rate_24hr_bbls: Optional[float] = Field(
        None, description="24-hour equivalent water rate in barrels"
    )
    choke_size_inches: Optional[float] = Field(None, description="Choke size in inches")
    flowing_tubing_pressure_psi: Optional[float] = Field(
        None, description="Flowing tubing pressure in PSI"
    )
    shut_in_tubing_pressure_psi: Optional[float] = Field(
        None, description="Shut-in tubing pressure in PSI"
    )
    test_method: Optional[str] = Field(
        None, description="Test method (e.g. swab test, flowing)"
    )


class Perforation(BaseModel):
    top_md_ft: Optional[float] = Field(
        None, description="Top perforation measured depth in feet"
    )
    bottom_md_ft: Optional[float] = Field(
        None, description="Bottom perforation measured depth in feet"
    )
    shots_per_ft: Optional[float] = Field(None, description="Shots per foot")
    gun_charge_diameter_in: Optional[float] = Field(
        None, description="Gun/charge diameter in inches"
    )
    gun_type: Optional[str] = Field(None, description="Gun or charge type")
    phase_angle_deg: Optional[float] = Field(None, description="Phase angle in degrees")
    formation_name: Optional[str] = Field(None, description="Perforated formation name")
    status: Optional[str] = Field(
        None, description="Status: open, squeezed, or isolated"
    )


class StimulationStage(BaseModel):
    treatment_type: Optional[str] = Field(
        None,
        description="Treatment type (e.g. acid breakdown, matrix acid, hydraulic fracture)",
    )
    stage_number: Optional[int] = Field(None, description="Stage number")
    fluid_volume_bbls: Optional[float] = Field(
        None, description="Fluid volume in barrels"
    )
    chemical_additives: Optional[str] = Field(
        None, description="Chemical additives / concentrations"
    )
    diverter_specs: Optional[str] = Field(
        None, description="Diverter or ball sealer specifications"
    )
    max_treating_pressure_psi: Optional[float] = Field(
        None, description="Maximum treating pressure in PSI"
    )
    avg_treating_pressure_psi: Optional[float] = Field(
        None, description="Average treating pressure in PSI"
    )
    injection_rate_bpm: Optional[float] = Field(
        None, description="Injection rate in barrels per minute"
    )
    isip_psi: Optional[float] = Field(
        None, description="Instantaneous Shut-In Pressure in PSI"
    )


class DownholeTubulars(BaseModel):
    tubing_od_in: Optional[float] = Field(
        None, description="Tubing outer diameter in inches"
    )
    tubing_weight_lbs_ft: Optional[float] = Field(
        None, description="Tubing weight in lbs/ft"
    )
    tubing_grade: Optional[str] = Field(None, description="Tubing steel grade")
    thread_type: Optional[str] = Field(None, description="Thread type")
    eot_depth_ft: Optional[float] = Field(
        None, description="End of Tubing depth in feet"
    )
    seating_nipple_depth_ft: Optional[float] = Field(
        None, description="Seating Nipple depth in feet"
    )
    tubing_anchor_catcher_depth_ft: Optional[float] = Field(
        None, description="Tubing Anchor Catcher depth in feet"
    )
    applied_pretension_lbs: Optional[float] = Field(
        None, description="Applied pretension in lbs"
    )


class CompletionStimulationData(BaseModel):
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
    ip_flow_test: Optional[IpFlowTest] = None
    perforations: list[Perforation] = Field(
        default_factory=list, description="Perforation intervals"
    )
    stimulation_stages: list[StimulationStage] = Field(
        default_factory=list, description="Stimulation / treatment stages"
    )
    downhole_tubulars: Optional[DownholeTubulars] = None


# ---------------------------------------------------------------------------
# Priority 2: Geological Formation Tops and Hydrocarbon Shows
# ---------------------------------------------------------------------------


class FormationTop(BaseModel):
    formation_name: Optional[str] = Field(None, description="Formation name")
    md_ft: Optional[float] = Field(None, description="Measured Depth in feet")
    tvd_ft: Optional[float] = Field(None, description="True Vertical Depth in feet")
    subsea_elevation_ft: Optional[float] = Field(
        None, description="Subsea elevation in feet"
    )
    pick_source: Optional[str] = Field(
        None, description="Source of the pick: E-log, mud log, or prognosis"
    )


class HydrocarbonShow(BaseModel):
    depth_from_ft: Optional[float] = Field(
        None, description="Interval top depth in feet"
    )
    depth_to_ft: Optional[float] = Field(
        None, description="Interval bottom depth in feet"
    )
    peak_gas_units: Optional[float] = Field(None, description="Peak gas units")
    baseline_gas_units: Optional[float] = Field(
        None, description="Baseline / background gas units"
    )
    c1_ppm: Optional[float] = Field(None, description="Methane (C1) in ppm")
    c2_ppm: Optional[float] = Field(None, description="Ethane (C2) in ppm")
    c3_ppm: Optional[float] = Field(None, description="Propane (C3) in ppm")
    c4_ppm: Optional[float] = Field(None, description="Butane (C4) in ppm")
    c5_ppm: Optional[float] = Field(None, description="Pentane (C5) in ppm")
    fluorescence: Optional[str] = Field(
        None, description="Visual sample fluorescence description"
    )
    cut: Optional[str] = Field(None, description="Sample cut description")
    lithology_description: Optional[str] = Field(
        None, description="Lithologic description"
    )


class GeologyData(BaseModel):
    formation_tops: list[FormationTop] = Field(
        default_factory=list, description="Formation tops matrix"
    )
    hydrocarbon_shows: list[HydrocarbonShow] = Field(
        default_factory=list, description="Hydrocarbon shows log"
    )


# ---------------------------------------------------------------------------
# Priority 3: Wellbore Architecture and Casing / Cement Integrity
# ---------------------------------------------------------------------------


class CasingString(BaseModel):
    string_type: Optional[str] = Field(
        None, description="String type: Surface, Intermediate, Production, Liner"
    )
    hole_size_in: Optional[float] = Field(None, description="Hole size in inches")
    casing_od_in: Optional[float] = Field(
        None, description="Casing outer diameter in inches"
    )
    nominal_weight_lbs_ft: Optional[float] = Field(
        None, description="Nominal weight in lbs/ft"
    )
    steel_grade: Optional[str] = Field(None, description="Steel grade")
    connection_type: Optional[str] = Field(None, description="Connection / thread type")
    setting_depth_ft: Optional[float] = Field(None, description="Setting depth in feet")
    burst_rating_psi: Optional[float] = Field(
        None, description="Burst pressure rating in PSI"
    )
    collapse_rating_psi: Optional[float] = Field(
        None, description="Collapse pressure rating in PSI"
    )


class CementOperation(BaseModel):
    slurry_volume_sacks: Optional[float] = Field(
        None, description="Slurry volume in sacks"
    )
    slurry_volume_bbls: Optional[float] = Field(
        None, description="Slurry volume in barrels"
    )
    lead_tail_formulation: Optional[str] = Field(
        None, description="Lead / tail formulation description"
    )
    slurry_density_ppg: Optional[float] = Field(
        None, description="Slurry density in ppg"
    )
    additives: Optional[str] = Field(None, description="Cement additives")
    displacement_volume_bbls: Optional[float] = Field(
        None, description="Displacement volume in barrels"
    )
    bump_pressure_psi: Optional[float] = Field(None, description="Bump pressure in PSI")
    surface_return_volume_bbls: Optional[float] = Field(
        None, description="Surface return volume in barrels"
    )


class MultiStageTool(BaseModel):
    stage_tool_depth_ft: Optional[float] = Field(
        None, description="Stage / DV tool depth in feet"
    )
    opening_pressure_psi: Optional[float] = Field(
        None, description="Tool opening pressure in PSI"
    )
    closing_pressure_psi: Optional[float] = Field(
        None, description="Tool closing pressure in PSI"
    )
    isolation_interval_from_ft: Optional[float] = Field(
        None, description="Stage isolation interval top in feet"
    )
    isolation_interval_to_ft: Optional[float] = Field(
        None, description="Stage isolation interval bottom in feet"
    )


class CementEvaluation(BaseModel):
    logged_toc_ft: Optional[float] = Field(
        None, description="Logged Top of Cement in feet"
    )
    verification_method: Optional[str] = Field(
        None,
        description="Verification: Cement Bond Log, temperature survey, or calculated",
    )
    bond_assessment: Optional[str] = Field(
        None, description="Qualitative bond assessment across target pay zones"
    )


class CasingCementData(BaseModel):
    casing_program: list[CasingString] = Field(
        default_factory=list, description="Casing program strings"
    )
    cementing_operations: list[CementOperation] = Field(
        default_factory=list, description="Cementing operations"
    )
    multi_stage_tools: list[MultiStageTool] = Field(
        default_factory=list, description="Multi-stage tooling & isolation"
    )
    cement_evaluation: Optional[CementEvaluation] = None


# ---------------------------------------------------------------------------
# Priority 4: Drilling Operations, Mud Program, and Geomechanics
# ---------------------------------------------------------------------------


class DrillingFluidParams(BaseModel):
    depth_ft: Optional[float] = Field(None, description="Depth in feet")
    mud_type: Optional[str] = Field(
        None, description="Mud type: water-based or oil-based invert"
    )
    mud_weight_ppg: Optional[float] = Field(None, description="Mud weight in ppg")
    funnel_viscosity_sec: Optional[float] = Field(
        None, description="Funnel viscosity in seconds"
    )
    fluid_loss_cc: Optional[float] = Field(
        None, description="Fluid loss / water loss in cc"
    )
    chlorides_ppm: Optional[float] = Field(None, description="Chlorides in ppm")
    oil_water_ratio: Optional[str] = Field(None, description="Oil / water ratio")


class BitRun(BaseModel):
    bit_number: Optional[int] = Field(None, description="Bit number")
    bit_size_in: Optional[float] = Field(None, description="Bit size in inches")
    manufacturer: Optional[str] = Field(None, description="Bit manufacturer")
    iadc_code: Optional[str] = Field(None, description="IADC code or cutter type")
    cutter_type: Optional[str] = Field(None, description="Cutter type")
    depth_in_ft: Optional[float] = Field(None, description="Depth in (start) in feet")
    depth_out_ft: Optional[float] = Field(None, description="Depth out (end) in feet")
    rotating_hours: Optional[float] = Field(None, description="Rotating hours")
    footage_drilled_ft: Optional[float] = Field(
        None, description="Footage drilled in feet"
    )
    avg_rop_ft_per_hr: Optional[float] = Field(
        None, description="Average Rate of Penetration in ft/hr"
    )


class WellboreEvent(BaseModel):
    event_type: Optional[str] = Field(
        None, description="Event type: lost circulation, gas kick, tight hole, etc."
    )
    depth_ft: Optional[float] = Field(None, description="Event depth in feet")
    description: Optional[str] = Field(None, description="Event description")
    treatment_type: Optional[str] = Field(
        None, description="Treatment / remediation applied"
    )


class DrillingData(BaseModel):
    drilling_fluid_params: list[DrillingFluidParams] = Field(
        default_factory=list, description="Drilling fluid properties by depth"
    )
    bit_runs: list[BitRun] = Field(
        default_factory=list, description="Bit performance / ROP records"
    )
    wellbore_events: list[WellboreEvent] = Field(
        default_factory=list, description="Wellbore conditions and NPT events"
    )


# ---------------------------------------------------------------------------
# Top-level payload for BigQuery JSON column
# ---------------------------------------------------------------------------


class WellfileExtractionPayload(BaseModel):
    completion_stimulation: Optional[CompletionStimulationData] = None
    geology: Optional[GeologyData] = None
    casing_cement: Optional[CasingCementData] = None
    drilling: Optional[DrillingData] = None


# ---------------------------------------------------------------------------
# Existing schemas (kept for backward compatibility)
# ---------------------------------------------------------------------------


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
    wellfile_data: Optional[WellfileExtractionPayload] = Field(
        None, description="Full structured extraction payload across all categories"
    )


class WellfileAgentRequest(BaseModel):
    api_number: str = Field(description="API well number to analyze")
