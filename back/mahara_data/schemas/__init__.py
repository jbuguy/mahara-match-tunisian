"""Inter-WP JSON contracts (Pydantic v2). Exported to JSON Schema under contracts/."""

from .application import ApplicationCreate, ApplicationRead, ApplicationStatusUpdate, HiringFeedback
from .common import SCHEMA_VERSION, ApiError, LanguageSkill, Location, Page
from .market import MarketDatasetCreate, MarketIndicatorRecord, SkillGapAggregate
from .matching import MatchResult, RankedMatches, Roadmap, RoadmapStep, ScoreBreakdown, ScoringWeights, SkillGapItem
from .offer import NormalizedJobOffer, OfferSkill, SalaryRange
from .profile import AppetenceVector, CandidateIdentity, CandidateProfile, ProfileSkill
from .taxonomy import (
    OccupationRead,
    SkillRead,
    SkillResolveRequest,
    SkillResolveResponse,
    SkillSuggestionRead,
    SkillSuggestionReview,
)
from .training import CertificationRecord, TrainingCourseRecord

# Contracts published as JSON Schema files, one per inter-WP payload.
PUBLISHED_CONTRACTS = {
    "candidate_profile": CandidateProfile,
    "candidate_identity": CandidateIdentity,
    "appetence_vector": AppetenceVector,
    "job_offer": NormalizedJobOffer,
    "match_result": MatchResult,
    "ranked_matches": RankedMatches,
    "roadmap": Roadmap,
    "application_create": ApplicationCreate,
    "application": ApplicationRead,
    "hiring_feedback": HiringFeedback,
    "skill": SkillRead,
    "skill_resolve_request": SkillResolveRequest,
    "skill_resolve_response": SkillResolveResponse,
    "skill_suggestion": SkillSuggestionRead,
    "skill_suggestion_review": SkillSuggestionReview,
    "occupation": OccupationRead,
    "market_dataset": MarketDatasetCreate,
    "market_indicator": MarketIndicatorRecord,
    "skill_gap_aggregate": SkillGapAggregate,
    "training_course": TrainingCourseRecord,
    "certification": CertificationRecord,
    "api_error": ApiError,
}

__all__ = [
    "PUBLISHED_CONTRACTS",
    "SCHEMA_VERSION",
    "ApiError",
    "AppetenceVector",
    "ApplicationCreate",
    "ApplicationRead",
    "ApplicationStatusUpdate",
    "CandidateIdentity",
    "CandidateProfile",
    "CertificationRecord",
    "HiringFeedback",
    "LanguageSkill",
    "Location",
    "MarketDatasetCreate",
    "MarketIndicatorRecord",
    "MatchResult",
    "NormalizedJobOffer",
    "OccupationRead",
    "OfferSkill",
    "Page",
    "ProfileSkill",
    "RankedMatches",
    "Roadmap",
    "RoadmapStep",
    "SalaryRange",
    "ScoreBreakdown",
    "ScoringWeights",
    "SkillGapAggregate",
    "SkillGapItem",
    "SkillRead",
    "SkillResolveRequest",
    "SkillResolveResponse",
    "SkillSuggestionRead",
    "SkillSuggestionReview",
    "TrainingCourseRecord",
]
