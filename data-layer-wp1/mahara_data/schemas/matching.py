"""Matching contracts. Producer: WP3. Consumers: WP4 (ranked candidates), WP6 (ranked offers, roadmaps), WP5."""

import math
import uuid
from datetime import datetime

from pydantic import Field, model_validator

from ..enums import GapType, RequirementLevel, RoadmapItemStatus, RoadmapStatus
from ..reference import DEFAULT_SCORING_WEIGHTS
from .common import Contract, ProficiencyLevel, Score, TaxonomyCode

# Tolerance for rounding when checking score_global against the weighted sum.
_SCORE_TOLERANCE = 0.5


class ScoringWeights(Contract):
    hard_skills: float = Field(default=DEFAULT_SCORING_WEIGHTS["hard_skills"], ge=0, le=1)
    experience: float = Field(default=DEFAULT_SCORING_WEIGHTS["experience"], ge=0, le=1)
    soft_skills: float = Field(default=DEFAULT_SCORING_WEIGHTS["soft_skills"], ge=0, le=1)
    location: float = Field(default=DEFAULT_SCORING_WEIGHTS["location"], ge=0, le=1)

    @model_validator(mode="after")
    def _sum_to_one(self) -> "ScoringWeights":
        total = self.hard_skills + self.experience + self.soft_skills + self.location
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"Scoring weights must sum to 1.0 (got {total})")
        return self


class ScoreBreakdown(Contract):
    hard_skills: Score
    experience: Score
    soft_skills: Score
    location: Score


class SkillGapItem(Contract):
    skill_code: TaxonomyCode
    gap_type: GapType
    requirement: RequirementLevel
    required_level: ProficiencyLevel
    current_level: ProficiencyLevel | None = None

    @model_validator(mode="after")
    def _levels(self) -> "SkillGapItem":
        if self.gap_type is GapType.MISSING and self.current_level is not None:
            raise ValueError("A missing skill has no current_level")
        if self.gap_type is GapType.INSUFFICIENT_LEVEL and (
            self.current_level is None or self.current_level >= self.required_level
        ):
            raise ValueError("insufficient_level requires current_level < required_level")
        return self


class MatchResult(Contract):
    match_id: uuid.UUID | None = None
    candidate_id: uuid.UUID
    job_offer_id: uuid.UUID
    score_global: Score
    breakdown: ScoreBreakdown
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    gaps: list[SkillGapItem] = Field(default_factory=list)
    model_version: str = Field(min_length=1, max_length=32)
    computed_at: datetime

    @model_validator(mode="after")
    def _global_is_weighted_sum(self) -> "MatchResult":
        b, w = self.breakdown, self.weights
        expected = (
            b.hard_skills * w.hard_skills
            + b.experience * w.experience
            + b.soft_skills * w.soft_skills
            + b.location * w.location
        )
        if abs(self.score_global - expected) > _SCORE_TOLERANCE:
            raise ValueError(f"score_global={self.score_global} does not match the weighted breakdown ({expected:.2f})")
        return self


class RankedMatches(Contract):
    """Offers for a candidate (WP6) or candidates for an offer (WP4), best first."""

    subject_id: uuid.UUID = Field(description="candidate_id or job_offer_id")
    subject_type: str = Field(pattern="^(candidate|job_offer)$")
    items: list[MatchResult]
    generated_at: datetime

    @model_validator(mode="after")
    def _sorted_desc(self) -> "RankedMatches":
        scores = [m.score_global for m in self.items]
        if scores != sorted(scores, reverse=True):
            raise ValueError("items must be sorted by score_global, descending")
        return self


class RoadmapStep(Contract):
    position: int = Field(ge=1)
    skill_code: TaxonomyCode
    training_course_id: uuid.UUID | None = None
    status: RoadmapItemStatus = RoadmapItemStatus.TODO


class Roadmap(Contract):
    roadmap_id: uuid.UUID | None = None
    candidate_id: uuid.UUID
    target_job_offer_id: uuid.UUID | None = None
    target_occupation_code: TaxonomyCode | None = None
    status: RoadmapStatus = RoadmapStatus.ACTIVE
    progress_pct: int = Field(default=0, ge=0, le=100)
    steps: list[RoadmapStep] = Field(min_length=1)
    model_version: str = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def _consistency(self) -> "Roadmap":
        if self.target_job_offer_id is None and self.target_occupation_code is None:
            raise ValueError("A roadmap targets a job offer or an occupation")
        positions = [s.position for s in self.steps]
        if sorted(positions) != list(range(1, len(positions) + 1)):
            raise ValueError("Step positions must be 1..n without gaps or duplicates")
        return self
