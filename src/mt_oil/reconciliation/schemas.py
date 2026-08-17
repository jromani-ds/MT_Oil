from pydantic import BaseModel, Field

from mt_oil.fracfocus.schemas import (
    AdditiveProfile,
    GasComponent,
    ProppantBreakdown,
)
from mt_oil.sanity.schemas import SanityFinding


class ProvenanceTag(BaseModel):
    source: str = Field(
        description="Data source: State Filing, FracFocus (Disclosed), or Reconciled"
    )
    field_name: str = Field(description="Name of the field this tag applies to")
    original_value: float | None = None
    original_unit: str | None = None
    volume_type: str | None = Field(
        None,
        description="Whether the reported volume is clean water, slurry, or unknown",
    )


class SourceView(BaseModel):
    total_clean_fluid_bbls: float | None = None
    total_proppant_lbs: float | None = None
    total_acid_gal: float | None = None
    proppant_concentration_ppa: float | None = None
    max_treating_pressure_psi: float | None = None
    tvd_ft: float | None = None
    provenance: list[ProvenanceTag] = Field(default_factory=list)


class VarianceReport(BaseModel):
    fluid_volume_delta_pct: float | None = Field(
        None, description="Variance % for fluid volume"
    )
    proppant_mass_delta_pct: float | None = Field(
        None, description="Variance % for proppant mass"
    )
    acid_volume_delta_pct: float | None = Field(
        None, description="Variance % for acid volume"
    )
    status: str = Field(description="Verified / Harmonized or Discrepancy Detected")
    stage_resolution_note: str | None = Field(
        None, description="Note about stage-vs-total resolution"
    )


class ReconciledStimulation(BaseModel):
    api_number: str = Field(description="10 or 14 digit API number")
    well_name: str | None = None
    treatment_class: str | None = Field(
        None,
        description="Treatment classification: Matrix Acidizing, Acid Frac, Hydraulic Fracture, etc.",
    )

    total_clean_fluid_bbls: float | None = None
    total_proppant_lbs: float | None = None
    total_acid_gal: float | None = None
    proppant_concentration_ppa: float | None = None
    base_fluid_type: str | None = None
    proppant_breakdown: ProppantBreakdown | None = None
    additives: AdditiveProfile | None = None
    gas_components: list[GasComponent] = Field(default_factory=list)
    net_perforated_ft: float | None = None
    acid_intensity_gal_per_ft: float | None = None
    foam_quality_pct: float | None = None
    glr_scf_per_bbl: float | None = None
    max_treating_pressure_psi: float | None = None

    state_source: SourceView = Field(default_factory=SourceView)
    fracfocus_source: SourceView = Field(default_factory=SourceView)

    variance: VarianceReport | None = None
    sanity_findings: list[SanityFinding] = Field(default_factory=list)
    badge: str = Field(
        default="green", description="Rollup badge: green, yellow, or red"
    )


class OverrideEntry(BaseModel):
    api_number: str
    field: str
    value: float
    note: str | None = None
    created_at: str | None = None
