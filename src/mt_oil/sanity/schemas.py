from pydantic import BaseModel, Field


class SanityFinding(BaseModel):
    rule: str = Field(
        description="Rule identifier (e.g. PPA, Choke64ths, TreatingPressure)"
    )
    severity: str = Field(description="green, yellow, or red")
    message: str = Field(description="Human-readable description")
    raw_value: float | None = None
    corrected_value: float | None = None
    corrected_unit: str | None = None
    note: str | None = None


class SanityBadge(BaseModel):
    severity: str = Field(
        default="green", description="Rollup severity of all findings"
    )
    findings: list[SanityFinding] = Field(default_factory=list)
