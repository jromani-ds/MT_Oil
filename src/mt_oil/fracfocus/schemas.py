from pydantic import BaseModel, Field


class ProppantBreakdown(BaseModel):
    silica_lbs: float | None = Field(
        None, description="Silica/quartz sand proppant mass in lbs"
    )
    resin_coated_lbs: float | None = Field(
        None, description="Resin-coated proppant mass in lbs"
    )
    ceramic_lbs: float | None = Field(
        None, description="Ceramic/sintered bauxite mass in lbs"
    )
    diverter_lbs: float | None = Field(
        None, description="Fluid diverter/micro-proppant mass in lbs"
    )
    other_lbs: float | None = Field(
        None, description="Unclassified proppant mass in lbs"
    )


class AdditiveProfile(BaseModel):
    friction_reducer_max_pct: float | None = Field(
        None, description="Max concentration of friction reducer (% by mass)"
    )
    scale_inhibitor_max_pct: float | None = Field(
        None, description="Max concentration of scale inhibitor (% by mass)"
    )
    biocide_max_pct: float | None = Field(
        None, description="Max concentration of biocide (% by mass)"
    )
    crosslinker_max_pct: float | None = Field(
        None, description="Max concentration of crosslinker (% by mass)"
    )
    surfactant_max_pct: float | None = Field(
        None, description="Max concentration of surfactant (% by mass)"
    )


class GasComponent(BaseModel):
    type: str = Field(description="Gas type: N2 or CO2")
    volume_scf: float | None = Field(None, description="Volume in standard cubic feet")
    mass_lbs: float | None = Field(None, description="Mass in pounds")
    liquid_bbl: float | None = Field(
        None, description="Liquid volume equivalent in barrels"
    )


class FracFocusDetailRow(BaseModel):
    api_wellno: str = Field(description="10 or 14 digit API number")
    cas_number: str | None = Field(None, description="CAS registry number")
    ingredient_name: str | None = Field(None, description="Ingredient name")
    supplier: str | None = Field(None, description="Supplier name")
    purpose: str | None = Field(None, description="Ingredient purpose")
    trade_name: str | None = Field(None, description="Trade or product name")
    mass_lbs: float | None = Field(None, description="Ingredient mass in pounds")
    percent_hfj: float | None = Field(None, description="Percent of HF job")
    calculation_type: str | None = Field(None, description="Calculation type for mass")
    job_start_date: str | None = Field(None, description="Job start date")
    job_end_date: str | None = Field(None, description="Job end date")
    operator: str | None = Field(None, description="Operating company")
    well_name: str | None = Field(None, description="Well name")
    ingested_at: str | None = Field(None, description="Ingestion timestamp")


class FracFocusWellAggregate(BaseModel):
    api_wellno: str = Field(description="10 or 14 digit API number")
    total_water_volume_gal: float | None = Field(
        None, description="Total base water volume in gallons"
    )
    total_nonwater_volume_gal: float | None = Field(
        None, description="Total base non-water volume in gallons"
    )
    total_proppant_lbs: float | None = Field(
        None, description="Total proppant mass in pounds"
    )
    total_acid_gal: float | None = Field(
        None, description="Total acid volume in gallons"
    )
    proppant_breakdown: ProppantBreakdown | None = None
    additives: AdditiveProfile | None = None
    base_fluid_type: str | None = Field(
        None, description="Primary base fluid: freshwater, produced water, brine"
    )
    gas_components: list[GasComponent] = Field(default_factory=list)
    tvd_ft: float | None = Field(None, description="True vertical depth in feet")
    job_start_date: str | None = Field(None, description="Job start date")
    job_end_date: str | None = Field(None, description="Job end date")
    operator: str | None = Field(None, description="Operating company")
    well_name: str | None = Field(None, description="Well name")
    ingested_at: str | None = Field(None, description="Ingestion timestamp")
