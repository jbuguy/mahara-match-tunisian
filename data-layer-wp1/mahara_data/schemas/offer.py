"""Normalized job offer (Fiche Offre Normalisée). Producer: WP4 (+ WP1 ingestion). Consumers: WP3, WP6."""

import uuid
from datetime import datetime

from pydantic import Field, model_validator

from ..enums import ContractType, EducationLevel, OfferSource, OfferStatus, RequirementLevel, WorkMode
from .common import SCHEMA_VERSION, Contract, LanguageSkill, Location, ProficiencyLevel, TaxonomyCode


class OfferSkill(Contract):
    skill_code: TaxonomyCode
    requirement: RequirementLevel
    min_level: ProficiencyLevel = 1


class SalaryRange(Contract):
    min_tnd: float | None = Field(default=None, ge=0)
    max_tnd: float | None = Field(default=None, ge=0)
    period: str = Field(default="month", pattern="^(hour|day|month)$")

    @model_validator(mode="after")
    def _ordered(self) -> "SalaryRange":
        if self.min_tnd is not None and self.max_tnd is not None and self.min_tnd > self.max_tnd:
            raise ValueError("min_tnd must be <= max_tnd")
        return self


class NormalizedJobOffer(Contract):
    schema_version: str = SCHEMA_VERSION
    offer_id: uuid.UUID | None = Field(default=None, description="Null on creation; assigned by WP1")
    employer_id: uuid.UUID | None = Field(default=None, description="Null for ministry-feed offers")
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    occupation_code: TaxonomyCode | None = None
    sector_code: TaxonomyCode | None = None
    contract_type: ContractType
    work_mode: WorkMode = WorkMode.ON_SITE
    location: Location
    positions_count: int = Field(default=1, ge=1, le=1000)
    min_years_experience: float = Field(default=0, ge=0, le=40)
    education_level_min: EducationLevel | None = None
    salary: SalaryRange | None = None
    skills: list[OfferSkill] = Field(min_length=1)
    languages_required: list[LanguageSkill] = Field(default_factory=list)
    status: OfferStatus = OfferStatus.DRAFT
    source: OfferSource = OfferSource.EMPLOYER_FORM
    published_at: datetime | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def _consistency(self) -> "NormalizedJobOffer":
        codes = [s.skill_code for s in self.skills]
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate skill_code in skills")
        if not any(s.requirement is RequirementLevel.REQUIRED for s in self.skills):
            raise ValueError("An offer needs at least one required skill")
        if self.source is OfferSource.EMPLOYER_FORM and self.employer_id is None:
            raise ValueError("employer_form offers must carry an employer_id")
        if self.published_at and self.expires_at and self.expires_at <= self.published_at:
            raise ValueError("expires_at must be after published_at")
        return self
