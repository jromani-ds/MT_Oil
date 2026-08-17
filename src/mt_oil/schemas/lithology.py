"""Pydantic schema for lithology classification."""

from pydantic import BaseModel, Field


class LithologyResult(BaseModel):
    lithology: str = Field(
        default="unknown", description="Primary lithology classification"
    )
    is_carbonate: bool = Field(
        default=False, description="Whether the formation is carbonate-dominated"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in the classification"
    )
    source: str = Field(
        default="builtin",
        description="Source of the classification (builtin, bq_cache, llm)",
    )
