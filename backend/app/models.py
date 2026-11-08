from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Float,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, Enum):
    CANDIDATE = "candidate"
    EMPLOYER = "employer"
    MINISTRY_ADMIN = "ministry_admin"
    TRAINING_PROVIDER = "training_provider"
    OPERATOR = "operator"


class OrganisationType(str, Enum):
    EMPLOYER = "employer"
    TRAINING_PROVIDER = "training_provider"


class JobApplicationStatus(str, Enum):
    SUBMITTED = "submitted"
    REVIEWING = "reviewing"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    INTERVIEW_COMPLETED = "interview_completed"
    OFFER_MADE = "offer_made"
    INTERVIEWED = "interviewed"
    OFFERED = "offered"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class JobOfferStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    PAUSED = "paused"
    CLOSED = "closed"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class PlanningSessionStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    ANALYSIS_READY = "analysis_ready"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class OrganisationVerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class OrganisationMemberRole(str, Enum):
    OWNER = "owner"
    ADMINISTRATOR = "administrator"
    RECRUITER = "recruiter"
    VIEWER = "viewer"


class InterviewStatus(str, Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class JobOfferDecisionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"


class CourseStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CourseDeliveryMode(str, Enum):
    ONLINE = "online"
    IN_PERSON = "in_person"
    HYBRID = "hybrid"


class CourseEnrollmentStatus(str, Enum):
    ENROLLED = "enrolled"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class ProfessionalProfileVisibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class ServiceListingStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    PAUSED = "paused"
    ARCHIVED = "archived"


class MissionStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class MissionProposalStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ServiceRequestStatus(str, Enum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    IN_PROGRESS = "in_progress"
    COMPLETION_REQUESTED = "completion_requested"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class TechnicalAssessmentStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class BehavioralAssessmentStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class InterviewTranscriptionStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Governorate(Base):
    __tablename__ = "governorates"

    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    name_fr: Mapped[str] = mapped_column(String(120), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)


class Municipality(Base):
    __tablename__ = "municipalities"
    __table_args__ = (
        UniqueConstraint(
            "governorate_code",
            "name_fr",
            name="uq_municipality_governorate_name_fr",
        ),
        Index("ix_municipalities_governorate_sort", "governorate_code", "sort_order"),
    )

    code: Mapped[str] = mapped_column(String(120), primary_key=True)
    governorate_code: Mapped[str] = mapped_column(
        ForeignKey("governorates.code", ondelete="RESTRICT"),
        nullable=False,
    )
    name_fr: Mapped[str] = mapped_column(String(160), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(160), nullable=False)
    delegation_name_fr: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        SqlEnum(
            Role,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    memberships: Mapped[list["OrganisationMembership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(String(3000), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    profile_details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    verification_status: Mapped[OrganisationVerificationStatus] = mapped_column(
        SqlEnum(
            OrganisationVerificationStatus,
            name="organisation_verification_status",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=OrganisationVerificationStatus.UNVERIFIED,
        nullable=False,
    )
    organisation_type: Mapped[OrganisationType] = mapped_column(
        SqlEnum(
            OrganisationType,
            name="organisation_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    memberships: Mapped[list["OrganisationMembership"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )


class OrganisationMembership(Base):
    __tablename__ = "organisation_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organisation_id", name="uq_membership_user_organisation"),
        Index("ix_membership_organisation_id", "organisation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organisation_id: Mapped[str] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[OrganisationMemberRole] = mapped_column(
        SqlEnum(
            OrganisationMemberRole,
            name="organisation_member_role",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=OrganisationMemberRole.OWNER,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="memberships")
    organisation: Mapped[Organisation] = relationship(back_populates="memberships")


class EmployerPlanningSession(Base):
    __tablename__ = "employer_planning_sessions"
    __table_args__ = (
        Index("ix_planning_sessions_organisation_updated", "organisation_id", "updated_at"),
        Index("ix_planning_sessions_created_by", "created_by_user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organisation_id: Mapped[str] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    project_type: Mapped[str] = mapped_column(String(40), default="other", nullable=False)
    status: Mapped[PlanningSessionStatus] = mapped_column(
        SqlEnum(
            PlanningSessionStatus,
            name="planning_session_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=PlanningSessionStatus.DRAFT,
        nullable=False,
    )
    project_summary: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    messages: Mapped[list["EmployerPlanningMessage"]] = relationship(
        back_populates="planning_session", cascade="all, delete-orphan"
    )
    documents: Mapped[list["EmployerPlanningDocument"]] = relationship(
        back_populates="planning_session", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["EmployerPlanningRecommendation"]] = relationship(
        back_populates="planning_session", cascade="all, delete-orphan"
    )


class EmployerPlanningMessage(Base):
    __tablename__ = "employer_planning_messages"
    __table_args__ = (
        Index("ix_planning_messages_session_created", "planning_session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    planning_session_id: Mapped[str] = mapped_column(
        ForeignKey("employer_planning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    planning_session: Mapped[EmployerPlanningSession] = relationship(back_populates="messages")


class EmployerPlanningDocument(Base):
    __tablename__ = "employer_planning_documents"
    __table_args__ = (
        Index("ix_planning_documents_session_created", "planning_session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    planning_session_id: Mapped[str] = mapped_column(
        ForeignKey("employer_planning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    processing_status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    planning_session: Mapped[EmployerPlanningSession] = relationship(back_populates="documents")


class EmployerPlanningRecommendation(Base):
    __tablename__ = "employer_planning_recommendations"
    __table_args__ = (
        Index("ix_planning_recommendations_session_created", "planning_session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    planning_session_id: Mapped[str] = mapped_column(
        ForeignKey("employer_planning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    recommendation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    sources: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )
    planning_session: Mapped[EmployerPlanningSession] = relationship(back_populates="recommendations")


class OrganisationVerificationRequest(Base):
    __tablename__ = "organisation_verification_requests"
    __table_args__ = (Index("ix_organisation_verification_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    submitted_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    supporting_information: Mapped[str] = mapped_column(String(4000), nullable=False)
    evidence_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[OrganisationVerificationStatus] = mapped_column(
        SqlEnum(OrganisationVerificationStatus, name="verification_request_status", native_enum=False, create_constraint=True, values_callable=lambda values: [member.value for member in values]),
        default=OrganisationVerificationStatus.PENDING,
        nullable=False,
    )
    reviewer_note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birth_year: Mapped[int | None] = mapped_column(nullable=True)
    profile_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    governorate_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    municipality_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    street_address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    education: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    experience: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    education_entries: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    experience_entries: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    professional_headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    employer_discoverable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SkillCatalogue(Base):
    __tablename__ = "skills_catalogue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    canonical_name_fr: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    canonical_name_en: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    user_id: Mapped[str] = mapped_column(ForeignKey("candidate_profiles.user_id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills_catalogue.id", ondelete="CASCADE"), primary_key=True)


class OfferSkill(Base):
    __tablename__ = "offer_skills"
    offer_id: Mapped[str] = mapped_column(ForeignKey("job_offers.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills_catalogue.id", ondelete="CASCADE"), primary_key=True)
    skill_type: Mapped[str] = mapped_column(String(10), primary_key=True)


class CourseSkill(Base):
    __tablename__ = "course_skills"
    course_id: Mapped[str] = mapped_column(ForeignKey("training_courses.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills_catalogue.id", ondelete="CASCADE"), primary_key=True)


class SkillAliasReview(Base):
    __tablename__ = "skill_alias_review"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    raw_skill: Mapped[str] = mapped_column(String(120), nullable=False)


class ProfessionalProfile(Base):
    __tablename__ = "professional_profiles"
    __table_args__ = (Index("ix_professional_profiles_visibility_location", "visibility", "location"),)

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    headline: Mapped[str] = mapped_column(String(200), nullable=False)
    introduction: Mapped[str] = mapped_column(String(5000), default="", nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    years_experience: Mapped[int | None] = mapped_column(nullable=True)
    visibility: Mapped[ProfessionalProfileVisibility] = mapped_column(
        SqlEnum(
            ProfessionalProfileVisibility,
            name="professional_profile_visibility",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=ProfessionalProfileVisibility.PRIVATE,
        nullable=False,
    )
    available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accepting_requests: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    availability: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    service_area: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    portfolio_items: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )


class ServiceListing(Base):
    __tablename__ = "service_listings"
    __table_args__ = (
        Index("ix_service_listings_status_created", "status", "created_at"),
        Index("ix_service_listings_owner_created", "owner_user_id", "created_at"),
        Index("ix_service_listings_category_status", "category", "status"),
        CheckConstraint("service_mode IN ('remote', 'provider_location', 'customer_location', 'flexible')", name="ck_service_listings_mode"),
        CheckConstraint("price_type IN ('fixed', 'hourly', 'starting_at', 'quote', 'negotiable')", name="ck_service_listings_price_type"),
        CheckConstraint("price_min IS NULL OR price_min >= 0", name="ck_service_listings_price_min_nonnegative"),
        CheckConstraint("price_max IS NULL OR price_max >= 0", name="ck_service_listings_price_max_nonnegative"),
        CheckConstraint("price_min IS NULL OR price_max IS NULL OR price_max >= price_min", name="ck_service_listings_price_range"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("professional_profiles.user_id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(5000), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    portfolio_items: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    service_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    price_type: Mapped[str] = mapped_column(String(30), nullable=False)
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[ServiceListingStatus] = mapped_column(
        SqlEnum(
            ServiceListingStatus,
            name="service_listing_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=ServiceListingStatus.DRAFT,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )


class ServiceRequest(Base):
    __tablename__ = "service_requests"
    __table_args__ = (
        Index("ix_service_requests_requester_created", "requester_user_id", "created_at"),
        Index("ix_service_requests_provider_status", "provider_user_id", "status"),
        Index("ix_service_requests_service_status", "service_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    service_id: Mapped[str] = mapped_column(ForeignKey("service_listings.id", ondelete="CASCADE"), nullable=False)
    requester_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(String(5000), nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_date: Mapped[date | None] = mapped_column(nullable=True)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    attachments: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    agreed_scope: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    report_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[ServiceRequestStatus] = mapped_column(SqlEnum(ServiceRequestStatus, name="service_request_status", native_enum=False, create_constraint=True, values_callable=lambda values: [member.value for member in values]), default=ServiceRequestStatus.REQUESTED, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ServiceReview(Base):
    __tablename__ = "service_reviews"
    __table_args__ = (
        UniqueConstraint("service_request_id", name="uq_service_review_request"),
        Index("ix_service_reviews_provider_created", "provider_user_id", "created_at"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_service_reviews_rating_range"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    service_request_id: Mapped[str] = mapped_column(ForeignKey("service_requests.id", ondelete="CASCADE"), nullable=False)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Mission(Base):
    __tablename__ = "missions"
    __table_args__ = (
        Index("ix_missions_status_created", "status", "created_at"),
        Index("ix_missions_publisher_created", "publisher_user_id", "created_at"),
        Index("ix_missions_organisation_status", "organisation_id", "status"),
        CheckConstraint("budget_min IS NULL OR budget_min >= 0", name="ck_missions_budget_min_nonnegative"),
        CheckConstraint("budget_max IS NULL OR budget_max >= 0", name="ck_missions_budget_max_nonnegative"),
        CheckConstraint("budget_min IS NULL OR budget_max IS NULL OR budget_max >= budget_min", name="ck_missions_budget_range"),
        CheckConstraint("work_mode IN ('remote', 'on_site', 'hybrid', 'flexible')", name="ck_missions_work_mode"),
        CheckConstraint("budget_type IN ('fixed', 'hourly', 'starting_at', 'quote', 'negotiable')", name="ck_missions_budget_type"),
        CheckConstraint("workers_needed >= 1", name="ck_missions_workers_positive"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    publisher_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organisation_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(5000), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    work_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    budget_type: Mapped[str] = mapped_column(String(30), nullable=False)
    budget_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    budget_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    expected_start_date: Mapped[date | None] = mapped_column(nullable=True)
    deadline: Mapped[date | None] = mapped_column(nullable=True)
    duration: Mapped[str | None] = mapped_column(String(120), nullable=True)
    workers_needed: Mapped[int] = mapped_column(default=1, nullable=False)
    status: Mapped[MissionStatus] = mapped_column(SqlEnum(MissionStatus, name="mission_status", native_enum=False, create_constraint=True, values_callable=lambda values: [member.value for member in values]), default=MissionStatus.DRAFT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class MissionProposal(Base):
    __tablename__ = "mission_proposals"
    __table_args__ = (
        UniqueConstraint("mission_id", "provider_user_id", name="uq_mission_proposal_provider"),
        Index("ix_mission_proposals_mission_status", "mission_id", "status"),
        Index("ix_mission_proposals_provider_created", "provider_user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message: Mapped[str] = mapped_column(String(5000), nullable=False)
    proposed_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_duration: Mapped[str | None] = mapped_column(String(120), nullable=True)
    portfolio_references: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    availability: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[MissionProposalStatus] = mapped_column(SqlEnum(MissionProposalStatus, name="mission_proposal_status", native_enum=False, create_constraint=True, values_callable=lambda values: [member.value for member in values]), default=MissionProposalStatus.SUBMITTED, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class MissionStatusHistory(Base):
    __tablename__ = "mission_status_history"
    __table_args__ = (Index("ix_mission_status_history_mission_created", "mission_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False)
    changed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    previous_status: Mapped[MissionStatus | None] = mapped_column(SqlEnum(MissionStatus, name="mission_history_previous_status", native_enum=False, create_constraint=False, values_callable=lambda values: [member.value for member in values]), nullable=True)
    new_status: Mapped[MissionStatus] = mapped_column(SqlEnum(MissionStatus, name="mission_history_new_status", native_enum=False, create_constraint=False, values_callable=lambda values: [member.value for member in values]), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
class CandidateRoadmapStep(Base):
    __tablename__ = "candidate_roadmap_steps"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_key", name="uq_candidate_roadmap_user_skill"),
        Index("ix_candidate_roadmap_steps_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    skill_key: Mapped[str] = mapped_column(String(60), nullable=False)
    skill: Mapped[str] = mapped_column(String(60), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CandidateAssistantSession(Base):
    __tablename__ = "candidate_assistant_sessions"
    __table_args__ = (
        Index("ix_candidate_assistant_sessions_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    messages: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CandidateTechnicalAssessment(Base):
    __tablename__ = "candidate_technical_assessments"
    __table_args__ = (
        Index(
            "ix_candidate_technical_assessments_candidate_created",
            "candidate_id",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_offer_id: Mapped[str] = mapped_column(
        ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False
    )
    skill: Mapped[str] = mapped_column(String(60), nullable=False)
    questions: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    status: Mapped[TechnicalAssessmentStatus] = mapped_column(
        SqlEnum(
            TechnicalAssessmentStatus,
            name="technical_assessment_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=TechnicalAssessmentStatus.IN_PROGRESS,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CandidateTechnicalAssessmentAnswer(Base):
    __tablename__ = "candidate_technical_assessment_answers"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "question_id",
            name="uq_technical_assessment_answer_question",
        ),
        Index(
            "ix_candidate_technical_assessment_answers_assessment",
            "assessment_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_technical_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[str] = mapped_column(String(20), nullable=False)
    answer: Mapped[str] = mapped_column(String(10000), nullable=False)
    evaluation: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class CandidateBehavioralAssessment(Base):
    __tablename__ = "candidate_behavioral_assessments"
    __table_args__ = (
        Index(
            "ix_candidate_behavioral_assessments_candidate_created",
            "candidate_id",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_offer_id: Mapped[str] = mapped_column(
        ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False
    )
    competency_id: Mapped[str] = mapped_column(String(60), nullable=False)
    competency_name: Mapped[str] = mapped_column(String(120), nullable=False)
    questions: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    status: Mapped[BehavioralAssessmentStatus] = mapped_column(
        SqlEnum(
            BehavioralAssessmentStatus,
            name="behavioral_assessment_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=BehavioralAssessmentStatus.IN_PROGRESS,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CandidateBehavioralAssessmentAnswer(Base):
    __tablename__ = "candidate_behavioral_assessment_answers"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "question_id",
            name="uq_behavioral_assessment_answer_question",
        ),
        Index(
            "ix_candidate_behavioral_assessment_answers_assessment",
            "assessment_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_behavioral_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[str] = mapped_column(String(20), nullable=False)
    answer: Mapped[str] = mapped_column(String(10000), nullable=False)
    evaluation: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class CandidateInterviewTranscription(Base):
    __tablename__ = "candidate_interview_transcriptions"
    __table_args__ = (
        Index(
            "ix_candidate_interview_transcriptions_candidate_created",
            "candidate_id",
            "created_at",
        ),
        Index(
            "ix_candidate_interview_transcriptions_assessment_question",
            "assessment_type",
            "assessment_id",
            "question_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assessment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    assessment_id: Mapped[str] = mapped_column(String(36), nullable=False)
    question_id: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[InterviewTranscriptionStatus] = mapped_column(
        SqlEnum(
            InterviewTranscriptionStatus,
            name="interview_transcription_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=InterviewTranscriptionStatus.QUEUED,
        nullable=False,
    )
    transcript: Mapped[str | None] = mapped_column(String(10000), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class JobOffer(Base):
    __tablename__ = "job_offers"
    __table_args__ = (Index("ix_job_offers_employer_created", "employer_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    employer_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(5000), nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    governorate_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    municipality_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    street_address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    required_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    employment_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    workplace_arrangement: Mapped[str | None] = mapped_column(String(20), nullable=True)
    positions_count: Mapped[int] = mapped_column(default=1, nullable=False)
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    application_deadline: Mapped[date | None] = mapped_column(nullable=True)
    planning_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("employer_planning_sessions.id", ondelete="SET NULL"), nullable=True
    )
    planning_recommendation_id: Mapped[str | None] = mapped_column(
        ForeignKey("employer_planning_recommendations.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[JobOfferStatus] = mapped_column(
        SqlEnum(
            JobOfferStatus,
            name="job_offer_status",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=JobOfferStatus.PUBLISHED,
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_offer_id", name="uq_application_candidate_offer"),
        Index("ix_job_applications_offer_created", "job_offer_id", "created_at"),
        Index("ix_job_applications_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_offer_id: Mapped[str] = mapped_column(
        ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[JobApplicationStatus] = mapped_column(
        SqlEnum(
            JobApplicationStatus,
            name="job_application_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=JobApplicationStatus.SUBMITTED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class JobApplicationStatusHistory(Base):
    __tablename__ = "job_application_status_history"
    __table_args__ = (Index("ix_application_status_history_application_created", "application_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    application_id: Mapped[str] = mapped_column(ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    from_status: Mapped[JobApplicationStatus | None] = mapped_column(
        SqlEnum(JobApplicationStatus, name="application_history_from_status", native_enum=False, create_constraint=False, values_callable=lambda values: [member.value for member in values]), nullable=True
    )
    to_status: Mapped[JobApplicationStatus] = mapped_column(
        SqlEnum(JobApplicationStatus, name="application_history_to_status", native_enum=False, create_constraint=False, values_callable=lambda values: [member.value for member in values]), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ApplicationStatusEvent(Base):
    __tablename__ = "application_status_events"
    __table_args__ = (Index("ix_application_status_events_application_changed", "application_id", "changed_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    application_id: Mapped[str] = mapped_column(ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(20), nullable=False)
    backfilled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class NationalIndicator(Base):
    __tablename__ = "national_indicators"
    __table_args__ = (
        UniqueConstraint("indicator_id", "year", name="uq_national_indicator_year"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    indicator_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    year: Mapped[int] = mapped_column(nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    source_document_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False
    )


def record_application_status_event(
    session,
    application: "JobApplication",
    from_status: JobApplicationStatus | None,
    to_status: JobApplicationStatus,
    changed_by: str,
) -> ApplicationStatusEvent:
    event = ApplicationStatusEvent(
        application_id=application.id,
        from_status=from_status.value if isinstance(from_status, JobApplicationStatus) else from_status,
        to_status=to_status.value if isinstance(to_status, JobApplicationStatus) else to_status,
        changed_by=changed_by,
    )
    session.add(event)
    return event


def application_age_group(birth_year: int | None, reference_year: int) -> str | None:
    if birth_year is None:
        return None
    age = reference_year - birth_year
    if 15 <= age <= 24:
        return "15-24"
    if 25 <= age <= 34:
        return "25-34"
    if age >= 35:
        return "35+"
    return None


class ApplicationNote(Base):
    __tablename__ = "application_notes"
    __table_args__ = (Index("ix_application_notes_application_created", "application_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    application_id: Mapped[str] = mapped_column(ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(String(10000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ApplicationEvaluation(Base):
    __tablename__ = "application_evaluations"
    __table_args__ = (UniqueConstraint("application_id", "evaluator_id", name="uq_application_evaluation_evaluator"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    application_id: Mapped[str] = mapped_column(ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False)
    evaluator_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    criteria: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    strengths: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    concerns: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class TalentPool(Base):
    __tablename__ = "talent_pools"
    __table_args__ = (UniqueConstraint("employer_id", "name", name="uq_talent_pool_employer_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    employer_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class TalentPoolMember(Base):
    __tablename__ = "talent_pool_members"
    __table_args__ = (UniqueConstraint("pool_id", "candidate_id", name="uq_talent_pool_candidate"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pool_id: Mapped[str] = mapped_column(ForeignKey("talent_pools.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    private_note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Conversation(Base):
    __tablename__ = "employer_conversations"
    __table_args__ = (UniqueConstraint("application_id", name="uq_employer_conversation_application"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    application_id: Mapped[str] = mapped_column(ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class Message(Base):
    __tablename__ = "employer_messages"
    __table_args__ = (Index("ix_employer_messages_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("employer_conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(String(10000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Interview(Base):
    __tablename__ = "employer_interviews"
    __table_args__ = (Index("ix_employer_interviews_application_start", "application_id", "starts_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    application_id: Mapped[str] = mapped_column(ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(default=60, nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    meeting_details: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[InterviewStatus] = mapped_column(SqlEnum(InterviewStatus, name="interview_status", native_enum=False, create_constraint=True, values_callable=lambda values: [member.value for member in values]), default=InterviewStatus.PROPOSED, nullable=False)
    feedback: Mapped[str | None] = mapped_column(String(10000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class InterviewParticipant(Base):
    __tablename__ = "employer_interview_participants"
    __table_args__ = (UniqueConstraint("interview_id", "user_id", name="uq_interview_participant_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    interview_id: Mapped[str] = mapped_column(ForeignKey("employer_interviews.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)


class InterviewFeedback(Base):
    __tablename__ = "employer_interview_feedback"
    __table_args__ = (UniqueConstraint("interview_id", "author_id", name="uq_interview_feedback_author"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    interview_id: Mapped[str] = mapped_column(ForeignKey("employer_interviews.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    criteria: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(10000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class JobOfferDecision(Base):
    __tablename__ = "job_offer_decisions"
    __table_args__ = (UniqueConstraint("application_id", name="uq_job_offer_decision_application"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    application_id: Mapped[str] = mapped_column(ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False)
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    response_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proposed_conditions: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[JobOfferDecisionStatus] = mapped_column(SqlEnum(JobOfferDecisionStatus, name="job_offer_decision_status", native_enum=False, create_constraint=True, values_callable=lambda values: [member.value for member in values]), default=JobOfferDecisionStatus.PENDING, nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmployerNotification(Base):
    __tablename__ = "employer_notifications"
    __table_args__ = (Index("ix_employer_notifications_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EmployerNotificationPreference(Base):
    __tablename__ = "employer_notification_preferences"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    notification_type: Mapped[str] = mapped_column(String(60), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TrainingCourse(Base):
    __tablename__ = "training_courses"
    __table_args__ = (
        Index("ix_training_courses_provider_status", "provider_id", "status"),
        Index("ix_training_courses_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(String(5000), nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    delivery_mode: Mapped[CourseDeliveryMode] = mapped_column(
        SqlEnum(
            CourseDeliveryMode,
            name="course_delivery_mode",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        nullable=False,
    )
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    governorate_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    municipality_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    street_address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    starts_on: Mapped[date | None] = mapped_column(nullable=True)
    ends_on: Mapped[date | None] = mapped_column(nullable=True)
    duration_hours: Mapped[int] = mapped_column(nullable=False)
    capacity: Mapped[int] = mapped_column(nullable=False)
    price_tnd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[CourseStatus] = mapped_column(
        SqlEnum(
            CourseStatus,
            name="course_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=CourseStatus.DRAFT,
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (
        UniqueConstraint("candidate_id", "course_id", name="uq_enrollment_candidate_course"),
        Index("ix_course_enrollments_course_status", "course_id", "status"),
        Index("ix_course_enrollments_candidate_created", "candidate_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("training_courses.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[CourseEnrollmentStatus] = mapped_column(
        SqlEnum(
            CourseEnrollmentStatus,
            name="course_enrollment_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        default=CourseEnrollmentStatus.ENROLLED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_created_at", "created_at"),
        Index("ix_audit_log_action", "action"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_role: Mapped[Role | None] = mapped_column(
        SqlEnum(
            Role,
            name="audit_actor_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [member.value for member in values],
        ),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


@event.listens_for(AuditEvent, "before_update")
def prevent_audit_event_update(mapper: object, connection: object, target: AuditEvent) -> None:
    raise RuntimeError("Audit events are append-only and cannot be updated.")


@event.listens_for(AuditEvent, "before_delete")
def prevent_audit_event_delete(mapper: object, connection: object, target: AuditEvent) -> None:
    raise RuntimeError("Audit events are append-only and cannot be deleted.")
