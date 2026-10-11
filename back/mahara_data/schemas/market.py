"""Ministry market-data ingestion (WP5 -> WP1) and skill-gap analytics (WP1 -> WP5)."""

import uuid
from datetime import date

from pydantic import Field, model_validator

from ..enums import MarketDataOrigin, MarketIndicatorType
from .common import Contract, GovernorateCode, TaxonomyCode


class MarketDatasetCreate(Contract):
    title: str = Field(min_length=3, max_length=200)
    origin: MarketDataOrigin
    publisher: str = Field(min_length=2, max_length=200)
    period_start: date
    period_end: date
    document_id: uuid.UUID | None = Field(default=None, description="Uploaded CSV/Excel file, if any")

    @model_validator(mode="after")
    def _period(self) -> "MarketDatasetCreate":
        if self.period_start > self.period_end:
            raise ValueError("period_start must be <= period_end")
        return self


class MarketIndicatorRecord(Contract):
    """One normalized row of a ministry dataset, after nomenclature alignment."""

    indicator_type: MarketIndicatorType
    occupation_code: TaxonomyCode | None = None
    skill_code: TaxonomyCode | None = None
    sector_code: TaxonomyCode | None = None
    governorate_code: GovernorateCode | None = None
    period_start: date
    period_end: date
    value: float
    unit: str = Field(pattern="^(count|percent|tnd)$")
    extra: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _consistency(self) -> "MarketIndicatorRecord":
        if self.period_start > self.period_end:
            raise ValueError("period_start must be <= period_end")
        if self.unit == "percent" and not 0 <= self.value <= 100:
            raise ValueError("percent values must be between 0 and 100")
        if self.indicator_type is MarketIndicatorType.SKILL_DEMAND and not self.skill_code:
            raise ValueError("skill_demand indicators need a skill_code")
        return self


class SkillGapAggregate(Contract):
    """Skill-gap cartography cell served to the ministry dashboard."""

    skill_code: TaxonomyCode
    governorate_code: GovernorateCode | None = None
    demand_count: int = Field(ge=0, description="Published offers requiring the skill")
    supply_count: int = Field(ge=0, description="Candidates holding the skill at the required level")
    gap_ratio: float = Field(ge=0, description="demand / max(supply, 1)")
    period_start: date
    period_end: date
