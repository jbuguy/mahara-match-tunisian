"""All ORM models. Importing this package registers every table on `Base.metadata`."""

from .accounts import AuthIdentity, User
from .candidates import (
    Candidate,
    CandidateDesiredOccupation,
    CandidateEducation,
    CandidateExperience,
    CandidatePII,
    CandidateSkill,
    ConversationSession,
    MockInterviewSession,
)
from .employers import Application, Employer, HiringFeedback, JobOffer, JobOfferSkill
from .market import MarketDataset, MarketIndicator
from .matching import MatchResult, Roadmap, RoadmapItem, SkillGap
from .platform import AuditLog, Document, Embedding, IngestionJob, MarketUploadPreview, NotificationOutbox
from .reference import Governorate, Sector
from .taxonomy import Occupation, OccupationSkill, Skill, SkillCategory, SkillRelation, SkillSuggestion
from .training import CandidateCertification, TrainingCourse, TrainingCourseSkill, TrainingProvider

__all__ = [
    "Application",
    "AuthIdentity",
    "AuditLog",
    "Candidate",
    "CandidateCertification",
    "CandidateDesiredOccupation",
    "CandidateEducation",
    "CandidateExperience",
    "CandidatePII",
    "CandidateSkill",
    "ConversationSession",
    "Document",
    "Embedding",
    "Employer",
    "Governorate",
    "HiringFeedback",
    "IngestionJob",
    "JobOffer",
    "JobOfferSkill",
    "MarketDataset",
    "MarketIndicator",
    "MarketUploadPreview",
    "MatchResult",
    "MockInterviewSession",
    "Occupation",
    "NotificationOutbox",
    "OccupationSkill",
    "Roadmap",
    "RoadmapItem",
    "Sector",
    "Skill",
    "SkillCategory",
    "SkillGap",
    "SkillRelation",
    "SkillSuggestion",
    "TrainingCourse",
    "TrainingCourseSkill",
    "TrainingProvider",
    "User",
]
