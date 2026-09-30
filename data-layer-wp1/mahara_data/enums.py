"""Shared enumerations for the WP1 data layer.

Every enum here is mirrored by a Postgres enum type in
``supabase/migrations/20260921000000_wp1_shared_schema.sql``. The values (not the
member names) are what is stored in the database and sent over the wire.
``tests/test_migration_sync.py`` fails if the two drift apart.
"""

import enum


class UserRole(str, enum.Enum):
    CANDIDATE = "candidate"
    EMPLOYER = "employer"
    ADMIN = "admin"
    MINISTRY = "ministry"
    TRAINING_PROVIDER = "training_provider"


class OnboardingPath(str, enum.Enum):
    CV_UPLOAD = "cv_upload"  # graduate with a CV (PDF/DOCX/image)
    DERJA_GUIDED_VOICE = "derja_guided_voice"  # non-literate: 5 basic audio questions
    DERJA_DETAILED = "derja_detailed"  # literate, no CV: detailed question tree


class LiteracyLevel(str, enum.Enum):
    NON_LITERATE = "non_literate"
    BASIC = "basic"
    LITERATE = "literate"


class EducationLevel(str, enum.Enum):
    NONE = "none"
    PRIMARY = "primary"
    LOWER_SECONDARY = "lower_secondary"
    BACCALAUREATE = "baccalaureate"
    VOCATIONAL_CAP = "vocational_cap"
    VOCATIONAL_BTP = "vocational_btp"
    VOCATIONAL_BTS = "vocational_bts"
    LICENCE = "licence"
    MASTER = "master"
    ENGINEER = "engineer"
    DOCTORATE = "doctorate"


class SkillType(str, enum.Enum):
    HARD = "hard"
    SOFT = "soft"
    LANGUAGE = "language"


class TaxonomyStatus(str, enum.Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    DEPRECATED = "deprecated"


class SkillRelationType(str, enum.Enum):
    BROADER = "broader"  # source is a specialisation of target
    RELATED = "related"
    EQUIVALENT = "equivalent"


class SuggestionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"


class SkillSource(str, enum.Enum):
    CV = "cv"
    DIALOGUE = "dialogue"
    CERTIFICATION = "certification"
    SELF_DECLARED = "self_declared"
    EMPLOYER_FEEDBACK = "employer_feedback"


class RequirementLevel(str, enum.Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class CompanySize(str, enum.Enum):
    # Same values as WP4's public.company_size type.
    SMALL = "1-10"
    MEDIUM = "11-50"
    LARGE = "51-200"
    ENTERPRISE = "200+"


class ContractType(str, enum.Enum):
    CDI = "cdi"
    CDD = "cdd"
    SIVP = "sivp"  # Stage d'Initiation à la Vie Professionnelle
    KARAMA = "karama"  # Contrat KARAMA
    INTERNSHIP = "internship"
    FREELANCE = "freelance"
    SEASONAL = "seasonal"
    DAILY_WORK = "daily_work"  # informal / day labour


class WorkMode(str, enum.Enum):
    ON_SITE = "on_site"
    REMOTE = "remote"
    HYBRID = "hybrid"


class OfferStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    CLOSED = "closed"
    FILLED = "filled"


class OfferSource(str, enum.Enum):
    EMPLOYER_FORM = "employer_form"
    MINISTRY_FEED = "ministry_feed"
    BULK_IMPORT = "bulk_import"


class ApplicationStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    VIEWED = "viewed"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    OFFER_MADE = "offer_made"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class HiringDecision(str, enum.Enum):
    HIRED = "hired"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    NO_SHOW = "no_show"


class GapType(str, enum.Enum):
    MISSING = "missing"
    INSUFFICIENT_LEVEL = "insufficient_level"


class RoadmapStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class RoadmapItemStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    SKIPPED = "skipped"


class CourseModality(str, enum.Enum):
    IN_PERSON = "in_person"
    ONLINE = "online"
    BLENDED = "blended"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class MarketDataOrigin(str, enum.Enum):
    OFFICIAL = "official"
    INFORMAL = "informal"
    STUDY = "study"


class MarketIndicatorType(str, enum.Enum):
    JOB_DEMAND = "job_demand"
    JOB_SUPPLY = "job_supply"
    VACANCIES = "vacancies"
    UNEMPLOYMENT_RATE = "unemployment_rate"
    MEDIAN_SALARY = "median_salary"
    SKILL_DEMAND = "skill_demand"


class ConversationChannel(str, enum.Enum):
    TEXT = "text"
    AUDIO = "audio"


class DocumentType(str, enum.Enum):
    CV = "cv"
    AUDIO = "audio"
    TRANSCRIPT = "transcript"
    CERTIFICATE = "certificate"
    MARKET_DATASET = "market_dataset"
    TRAINING_CATALOG = "training_catalog"
    OTHER = "other"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionSource(str, enum.Enum):
    CV_UPLOAD = "cv_upload"
    CONVERSATION = "conversation"
    EMPLOYER_OFFER = "employer_offer"
    MINISTRY_MARKET = "ministry_market"
    TRAINING_CATALOG = "training_catalog"


class EmbeddingEntity(str, enum.Enum):
    CANDIDATE = "candidate"
    JOB_OFFER = "job_offer"
    SKILL = "skill"
    OCCUPATION = "occupation"
    TRAINING_COURSE = "training_course"
