"""Skills ontology and occupations. Owner: WP1. Governance (validation): WP5 admin."""

import uuid

from pydantic import Field

from ..enums import IngestionSource, RequirementLevel, SkillRelationType, SkillType, SuggestionStatus, TaxonomyStatus
from .common import Contract, TaxonomyCode


class SkillRead(Contract):
    skill_id: uuid.UUID
    code: TaxonomyCode
    label_fr: str
    label_ar: str | None = None
    label_derja: str | None = None
    alt_labels: list[str] = Field(default_factory=list)
    skill_type: SkillType
    category_code: TaxonomyCode | None = None
    status: TaxonomyStatus
    esco_uri: str | None = None
    version: int = Field(ge=1)


class SkillRelationRead(Contract):
    source_code: TaxonomyCode
    target_code: TaxonomyCode
    relation_type: SkillRelationType


class SkillResolveRequest(Contract):
    """Free-text label -> taxonomy code, used by WP2 and WP4 while structuring input."""

    label: str = Field(min_length=1, max_length=200)
    language: str | None = Field(default=None, max_length=8)
    skill_type: SkillType | None = None
    top_k: int = Field(default=3, ge=1, le=10)


class SkillCandidateMatch(Contract):
    skill: SkillRead
    similarity: float = Field(ge=0, le=1)


class SkillResolveResponse(Contract):
    label: str
    matches: list[SkillCandidateMatch]
    suggestion_id: uuid.UUID | None = Field(default=None, description="Set when no match was good enough")


class SkillSuggestionRead(Contract):
    suggestion_id: uuid.UUID
    proposed_label: str
    normalized_label: str
    skill_type: SkillType | None = None
    source: IngestionSource
    occurrences: int = Field(ge=1)
    status: SuggestionStatus
    resolved_skill_code: TaxonomyCode | None = None


class SkillSuggestionReview(Contract):
    status: SuggestionStatus
    resolved_skill_code: TaxonomyCode | None = Field(default=None, description="Required when status is merged")


class OccupationSkillRead(Contract):
    skill_code: TaxonomyCode
    requirement: RequirementLevel


class OccupationRead(Contract):
    occupation_id: uuid.UUID
    code: TaxonomyCode
    isco_code: str | None = None
    title_fr: str
    title_ar: str | None = None
    alt_titles: list[str] = Field(default_factory=list)
    sector_code: TaxonomyCode | None = None
    status: TaxonomyStatus
    skills: list[OccupationSkillRead] = Field(default_factory=list)
