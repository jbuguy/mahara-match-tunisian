from datetime import date, datetime
from decimal import Decimal
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import (
    CourseDeliveryMode,
    CourseEnrollmentStatus,
    CourseStatus,
    JobApplicationStatus,
    JobOfferStatus,
    ProfessionalProfileVisibility,
    Role,
    ServiceListingStatus,
)


def normalize_skills(value: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for skill in value:
        clean_skill = skill.strip()
        if not clean_skill:
            continue
        if len(clean_skill) > 60:
            raise ValueError("Each skill must be 60 characters or fewer.")
        key = clean_skill.casefold()
        if len(key) > 60:
            raise ValueError("Each normalized skill must be 60 characters or fewer.")
        if key not in seen:
            normalized.append(clean_skill)
            seen.add(key)
    return normalized


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()


class CandidateRegistrationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: Role


class OrganisationProductService(BaseModel):
    name: str = Field(default="", max_length=160)
    description: str = Field(default="", max_length=1000)
    category: str = Field(default="", max_length=120)


class OrganisationTeam(BaseModel):
    name: str = Field(default="", max_length=160)
    responsibilities: str = Field(default="", max_length=1000)
    roles: str = Field(default="", max_length=500)


class OrganisationProfileDetails(BaseModel):
    activities: str = Field(default="", max_length=2000)
    mission: str = Field(default="", max_length=1000)
    vision: str = Field(default="", max_length=1000)
    values: str = Field(default="", max_length=1000)
    culture: str = Field(default="", max_length=1500)
    working_environment: str = Field(default="", max_length=1500)
    products_services: list[OrganisationProductService] = Field(default_factory=list, max_length=30)
    teams: list[OrganisationTeam] = Field(default_factory=list, max_length=30)
    candidate_profiles: str = Field(default="", max_length=1500)
    technical_skills: str = Field(default="", max_length=1000)
    soft_skills: str = Field(default="", max_length=1000)
    work_preferences: str = Field(default="", max_length=1000)
    other_preferences: str = Field(default="", max_length=1000)


class OrganisationProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    sector: str | None = Field(default=None, max_length=120)
    size: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=3000)
    phone: str | None = Field(default=None, max_length=40)
    contact_email: str | None = Field(default=None, max_length=320)
    location: str | None = Field(default=None, max_length=200)
    profile_details: OrganisationProfileDetails | None = None

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        clean = value.strip()
        if len(clean) < 2:
            raise ValueError("Organisation name must contain at least two characters.")
        return clean

    @field_validator("website")
    @classmethod
    def validate_website(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        clean = value.strip()
        if not clean.startswith(("https://", "http://")):
            raise ValueError("Website must start with http:// or https://.")
        return clean


class OrganisationProfileResponse(OrganisationProfileUpdate):
    id: str
    organisation_type: str
    verification_status: str = "unverified"
    profile_details: OrganisationProfileDetails = Field(default_factory=OrganisationProfileDetails)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class AuditEventResponse(BaseModel):
    id: str
    action: str
    resource_type: str | None
    actor_role: Role | None
    created_at: datetime


class EducationEntry(BaseModel):
    degree: str = Field(default="", max_length=200)
    institution: str = Field(default="", max_length=200)
    field_of_study: str = Field(default="", max_length=200)
    start_date: str = Field(default="", max_length=40)
    end_date: str = Field(default="", max_length=40)
    currently_studying: bool = False


class ExperienceEntry(BaseModel):
    job_title: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=200)
    employment_type: str = Field(default="", max_length=80)
    location: str = Field(default="", max_length=120)
    start_date: str = Field(default="", max_length=40)
    end_date: str = Field(default="", max_length=40)
    currently_working: bool = False
    responsibilities: str = Field(default="", max_length=3000)


class CandidateProfileUpdate(BaseModel):
    skills: list[str] | None = Field(default=None, max_length=30)
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=120)
    education: str | None = Field(default=None, max_length=5000)
    experience: str | None = Field(default=None, max_length=5000)
    education_entries: list[EducationEntry] | None = Field(default=None, max_length=30)
    experience_entries: list[ExperienceEntry] | None = Field(default=None, max_length=30)
    professional_headline: str | None = Field(default=None, max_length=200)
    employer_discoverable: bool | None = None

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, value: list[str] | None) -> list[str] | None:
        return normalize_skills(value) if value is not None else None

    @field_validator("full_name", "phone", "location", "education", "experience", "professional_headline")
    @classmethod
    def trim_profile_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def require_profile_field(self) -> "CandidateProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one profile field must be provided.")
        return self


class CandidateProfileResponse(BaseModel):
    user_id: str
    skills: list[str]
    full_name: str | None = None
    phone: str | None = None
    location: str | None = None
    education: str | None = None
    experience: str | None = None
    education_entries: list[EducationEntry] = Field(default_factory=list)
    experience_entries: list[ExperienceEntry] = Field(default_factory=list)
    professional_headline: str | None = None
    employer_discoverable: bool = False
    updated_at: datetime | None = None


class ProfessionalProfileFields(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    headline: str = Field(min_length=2, max_length=200)
    introduction: str = Field(default="", max_length=5000)
    photo_url: str | None = Field(default=None, max_length=1000)
    location: str | None = Field(default=None, max_length=120)
    languages: list[str] = Field(default_factory=list, max_length=12)
    skills: list[str] = Field(default_factory=list, max_length=30)
    years_experience: int | None = Field(default=None, ge=0, le=80)
    visibility: ProfessionalProfileVisibility = ProfessionalProfileVisibility.PRIVATE
    available: bool = True
    accepting_requests: bool = True
    availability: dict[str, object] = Field(default_factory=dict)

    @field_validator("display_name", "headline", "introduction")
    @classmethod
    def trim_professional_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("location")
    @classmethod
    def trim_professional_location(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("skills")
    @classmethod
    def normalize_professional_skills(cls, value: list[str]) -> list[str]:
        return normalize_skills(value)

    @field_validator("languages")
    @classmethod
    def normalize_languages(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class ProfessionalProfileResponse(ProfessionalProfileFields):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    created_at: datetime
    updated_at: datetime


class PublicServiceListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_user_id: str
    title: str
    description: str
    category: str
    skills: list[str]
    location: str | None
    service_mode: str
    price_type: str
    price_min: Decimal | None
    price_max: Decimal | None
    created_at: datetime


class ServiceListingFields(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    category: str = Field(min_length=2, max_length=120)
    skills: list[str] = Field(default_factory=list, max_length=30)
    location: str | None = Field(default=None, max_length=120)
    service_mode: Literal["remote", "provider_location", "customer_location", "flexible"]
    price_type: Literal["fixed", "hourly", "starting_at", "quote", "negotiable"] = "quote"
    price_min: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    price_max: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    @field_validator("title", "description", "category")
    @classmethod
    def trim_service_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("skills")
    @classmethod
    def normalize_service_skills(cls, value: list[str]) -> list[str]:
        return normalize_skills(value)

    @model_validator(mode="after")
    def validate_service_listing(self) -> "ServiceListingFields":
        if self.price_min is not None and self.price_max is not None and self.price_max < self.price_min:
            raise ValueError("Maximum price must be greater than or equal to minimum price.")
        if self.service_mode != "remote" and not self.location:
            raise ValueError("A location is required for in-person service modes.")
        return self


class ServiceListingCreate(ServiceListingFields):
    pass


class ServiceListingResponse(ServiceListingFields):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_user_id: str
    status: ServiceListingStatus
    created_at: datetime
    updated_at: datetime


class ServiceListingStatusUpdate(BaseModel):
    status: ServiceListingStatus


class PublicProfessionalProfileResponse(BaseModel):
    id: str
    display_name: str
    headline: str
    introduction: str
    photo_url: str | None
    location: str | None
    languages: list[str]
    skills: list[str]
    years_experience: int | None
    available: bool
    accepting_requests: bool
    availability: dict[str, object]
    services: list[PublicServiceListingResponse]


class PublicProfessionalSearchPage(BaseModel):
    items: list[PublicProfessionalProfileResponse]
    total: int
    limit: int
    offset: int


class PublicServiceSearchPage(BaseModel):
    items: list[PublicServiceListingResponse]
    total: int
    limit: int
    offset: int


class AssistantMessage(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=3000)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in {"user", "assistant"}:
            raise ValueError("Message role must be user or assistant.")
        return value

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Message content cannot be blank.")
        return clean


class CandidateAssistantRequest(BaseModel):
    messages: list[AssistantMessage] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def require_user_message_last(self) -> "CandidateAssistantRequest":
        if self.messages[-1].role != "user":
            raise ValueError("The last assistant message must be from the candidate.")
        return self


class CandidateProfileDraft(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=120)
    education: str | None = Field(default=None, max_length=5000)
    experience: str | None = Field(default=None, max_length=5000)
    education_entries: list[EducationEntry] | None = Field(default=None, max_length=30)
    experience_entries: list[ExperienceEntry] | None = Field(default=None, max_length=30)
    skills: list[str] | None = Field(default=None, max_length=30)


class CandidateAssistantResponse(BaseModel):
    reply: str = Field(min_length=1, max_length=3000)
    profile_updates: CandidateProfileDraft = Field(default_factory=CandidateProfileDraft)


class CandidateAssistantSpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)

    @field_validator("text")
    @classmethod
    def trim_text(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Text cannot be blank.")
        return clean


class CandidateAssistantSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    messages: list[AssistantMessage]
    created_at: datetime
    updated_at: datetime


class CandidateAssistantSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class CandidateAssistantMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=3000)

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Message content cannot be blank.")
        return clean


class CandidateAssistantSessionRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Conversation title cannot be blank.")
        return clean


class JobOfferCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    location: str = Field(min_length=2, max_length=120)
    required_skills: list[str] = Field(min_length=1, max_length=30)
    preferred_skills: list[str] = Field(default_factory=list, max_length=30)
    status: JobOfferStatus = JobOfferStatus.PUBLISHED

    @field_validator("title", "description", "location")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("required_skills")
    @classmethod
    def clean_skills(cls, value: list[str]) -> list[str]:
        normalized = normalize_skills(value)
        if not normalized:
            raise ValueError("At least one required skill is needed.")
        return normalized

    @field_validator("preferred_skills")
    @classmethod
    def clean_preferred_skills(cls, value: list[str]) -> list[str]:
        return normalize_skills(value)

    @model_validator(mode="after")
    def reject_blank_text(self) -> "JobOfferCreate":
        if not self.title or not self.description or not self.location:
            raise ValueError("Title, description, and location cannot be blank.")
        return self


class JobOfferGenerationRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=3000)

    @field_validator("prompt")
    @classmethod
    def trim_prompt(cls, value: str) -> str:
        return value.strip()


class JobOfferSuggestion(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    location: str = Field(min_length=2, max_length=120)
    required_skills: list[str] = Field(default_factory=list, max_length=30)
    preferred_skills: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("required_skills", "preferred_skills")
    @classmethod
    def clean_suggested_skills(cls, value: list[str]) -> list[str]:
        return normalize_skills(value)


class JobOfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    location: str
    required_skills: list[str]
    preferred_skills: list[str] = Field(default_factory=list)
    status: JobOfferStatus = JobOfferStatus.PUBLISHED
    employment_type: str | None = None
    workplace_arrangement: str | None = None
    positions_count: int = 1
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    application_deadline: date | None = None
    published_at: datetime | None = None
    created_at: datetime


class PublicJobOfferPage(BaseModel):
    items: list[JobOfferResponse]
    total: int
    limit: int
    offset: int


class JobOfferStatusUpdate(BaseModel):
    status: JobOfferStatus


class ApplicationStatusHistoryResponse(BaseModel):
    id: str
    from_status: JobApplicationStatus | None
    to_status: JobApplicationStatus
    created_at: datetime


class CandidateDiscoveryResponse(BaseModel):
    candidate_id: str
    professional_headline: str | None
    skills: list[str]
    location: str | None
    experience_summary: list[dict[str, object]]
    education_summary: list[dict[str, object]]
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class TalentPoolCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A talent pool name is required.")
        return value.strip()


class TalentPoolResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    candidate_count: int


class TalentPoolMemberRequest(BaseModel):
    candidate_id: str
    private_note: str | None = Field(default=None, max_length=2000)


class TalentPoolMemberResponse(BaseModel):
    candidate_id: str
    professional_headline: str | None
    skills: list[str]
    location: str | None
    private_note: str | None
    created_at: datetime


class ApplicationNoteCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)

    @field_validator("content")
    @classmethod
    def trim_note(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A note cannot be blank.")
        return value.strip()


class ApplicationNoteResponse(BaseModel):
    id: str
    content: str
    created_at: datetime


class ApplicationEvaluationRequest(BaseModel):
    criteria: list[dict[str, object]] = Field(default_factory=list, max_length=20)
    strengths: str | None = Field(default=None, max_length=5000)
    concerns: str | None = Field(default=None, max_length=5000)


class ApplicationEvaluationResponse(BaseModel):
    id: str
    criteria: list[dict[str, object]]
    strengths: str | None
    concerns: str | None
    updated_at: datetime


class ConversationResponse(BaseModel):
    id: str
    application_id: str
    candidate_name: str | None
    job_title: str
    updated_at: datetime
    unread_count: int


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)

    @field_validator("content")
    @classmethod
    def trim_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A message cannot be blank.")
        return value.strip()


class MessageResponse(BaseModel):
    id: str
    sender_id: str
    content: str
    created_at: datetime
    read_at: datetime | None


class InterviewCreateRequest(BaseModel):
    application_id: str
    starts_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=480)
    format: Literal["online", "in_person"]
    meeting_details: str | None = Field(default=None, max_length=2000)
    interviewer_ids: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("starts_at")
    @classmethod
    def require_timezone_aware_start(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Interview start time must include a timezone.")
        return value


class InterviewStatusUpdate(BaseModel):
    status: Literal["confirmed", "completed", "cancelled", "no_show"]


class InterviewResponse(BaseModel):
    id: str
    application_id: str
    job_title: str
    candidate_name: str | None
    starts_at: datetime
    duration_minutes: int
    format: str
    meeting_details: str | None
    status: str


class InterviewFeedbackRequest(BaseModel):
    criteria: list[dict[str, object]] = Field(default_factory=list, max_length=20)
    recommendation: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=10000)


class InterviewFeedbackResponse(BaseModel):
    id: str
    criteria: list[dict[str, object]]
    recommendation: str | None
    notes: str | None
    created_at: datetime


class JobOfferDecisionCreateRequest(BaseModel):
    response_deadline: datetime | None = None
    proposed_conditions: dict[str, object] = Field(default_factory=dict)

    @field_validator("response_deadline")
    @classmethod
    def validate_decision_deadline(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Decision deadline must include a timezone.")
        return value


class JobOfferDecisionUpdateRequest(BaseModel):
    status: Literal["accepted", "declined"]


class JobOfferDecisionResponse(BaseModel):
    id: str
    application_id: str
    job_title: str
    status: str
    offered_at: datetime
    response_deadline: datetime | None
    proposed_conditions: dict[str, object]
    responded_at: datetime | None


class NotificationResponse(BaseModel):
    id: str
    notification_type: str
    title: str
    body: str
    resource_type: str | None
    resource_id: str | None
    read_at: datetime | None
    created_at: datetime


class OrganisationVerificationCreateRequest(BaseModel):
    supporting_information: str = Field(min_length=20, max_length=4000)
    evidence_url: str | None = Field(default=None, max_length=1000)

    @field_validator("supporting_information")
    @classmethod
    def trim_verification_information(cls, value: str) -> str:
        return value.strip()


class OrganisationVerificationResponse(BaseModel):
    id: str
    organisation_id: str | None = None
    organisation_name: str | None = None
    status: str
    supporting_information: str
    evidence_url: str | None
    reviewer_note: str | None
    created_at: datetime


class OrganisationVerificationReviewRequest(BaseModel):
    status: Literal["verified", "rejected"]
    reviewer_note: str = Field(min_length=10, max_length=2000)


class NotificationPreferenceResponse(BaseModel):
    notification_type: str
    enabled: bool


class NotificationPreferenceUpdate(BaseModel):
    enabled: bool


class EmployerAnalyticsResponse(BaseModel):
    total_applications: int
    applications_by_status: dict[str, int]
    applications_per_offer: list[dict[str, object]]
    shortlisted: int
    interviews: int
    hires_reported: int
    rejected: int
    withdrawn: int
    application_to_interview_percent: int | None
    interview_to_hire_percent: int | None
    average_time_to_first_review_hours: float | None
    has_sufficient_data: bool


class JobMatchResponse(JobOfferResponse):
    match_score: int
    matched_skills: list[str]
    missing_skills: list[str]


class JobApplicationResponse(BaseModel):
    id: str
    job_offer_id: str
    job_title: str
    location: str
    status: JobApplicationStatus
    created_at: datetime
    updated_at: datetime


class EmployerApplicationResponse(JobApplicationResponse):
    candidate_name: str | None
    candidate_location: str | None
    candidate_skills: list[str]


class EmployerApplicationDetailResponse(EmployerApplicationResponse):
    professional_headline: str | None
    education_entries: list[dict[str, object]]
    experience_entries: list[dict[str, object]]
    status_history: list[ApplicationStatusHistoryResponse]


class JobApplicationStatusUpdate(BaseModel):
    status: JobApplicationStatus


class TrainingCourseFields(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    summary: str = Field(min_length=10, max_length=5000)
    skills: list[str] = Field(min_length=1, max_length=30)
    delivery_mode: CourseDeliveryMode
    location: str | None = Field(default=None, max_length=120)
    starts_on: date | None = None
    ends_on: date | None = None
    duration_hours: int = Field(ge=1, le=2000)
    capacity: int = Field(ge=1, le=10000)
    price_tnd: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    status: CourseStatus = CourseStatus.DRAFT

    @field_validator("title", "summary")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("location")
    @classmethod
    def trim_location(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("skills")
    @classmethod
    def clean_course_skills(cls, value: list[str]) -> list[str]:
        normalized = normalize_skills(value)
        if not normalized:
            raise ValueError("At least one course skill is required.")
        return normalized

    @model_validator(mode="after")
    def validate_course_details(self) -> "TrainingCourseFields":
        if not self.title or not self.summary:
            raise ValueError("Title and summary cannot be blank.")
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("Course end date must be on or after its start date.")
        if (
            self.delivery_mode in {CourseDeliveryMode.IN_PERSON, CourseDeliveryMode.HYBRID}
            and not self.location
        ):
            raise ValueError("A location is required for in-person or hybrid courses.")
        return self


class TrainingCourseCreate(TrainingCourseFields):
    pass


class TrainingCourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: str
    skills: list[str]
    delivery_mode: CourseDeliveryMode
    location: str | None
    starts_on: date | None
    ends_on: date | None
    duration_hours: int
    capacity: int
    price_tnd: Decimal | None
    status: CourseStatus
    created_at: datetime
    updated_at: datetime
    enrollment_count: int = 0
    completed_count: int = 0


class PublicTrainingCourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: str
    skills: list[str]
    delivery_mode: CourseDeliveryMode
    location: str | None
    starts_on: date | None
    ends_on: date | None
    duration_hours: int
    price_tnd: Decimal | None


class PublicTrainingSearchPage(BaseModel):
    items: list[PublicTrainingCourseResponse]
    total: int
    limit: int
    offset: int


class CourseEnrollmentResponse(BaseModel):
    id: str
    course_id: str
    course_title: str
    status: CourseEnrollmentStatus
    created_at: datetime
    updated_at: datetime


class ProviderCourseEnrollmentResponse(CourseEnrollmentResponse):
    candidate_name: str | None
    candidate_location: str | None
    candidate_skills: list[str]


class CourseEnrollmentStatusUpdate(BaseModel):
    status: CourseEnrollmentStatus


class SkillDemandIndicator(BaseModel):
    skill: str
    offer_count: int


class ApplicationStatusIndicator(BaseModel):
    status: JobApplicationStatus
    count: int


class AdminIndicatorsResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    candidate_registrations: int
    organisations: int
    published_job_offers: int
    applications_total: int
    applications_by_status: list[ApplicationStatusIndicator]
    closed_applications: int
    hired_applications: int
    hire_rate_percent: float | None
    top_skills: list[SkillDemandIndicator]
    published_courses: int
    active_enrollments: int
    course_completions: int


class CandidateRoadmapStepResponse(BaseModel):
    skill: str
    skill_key: str
    required_by: list[str]
    offer_count: int
    completed: bool


class CandidateRoadmapResponse(BaseModel):
    steps: list[CandidateRoadmapStepResponse]
    completed_steps: int
    total_steps: int
    progress_percent: int


class CandidateRoadmapStepUpdate(BaseModel):
    skill: str = Field(min_length=1, max_length=60)
    completed: bool

    @field_validator("skill")
    @classmethod
    def trim_skill(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Skill cannot be blank.")
        return clean


class CandidateInterviewRoleResponse(BaseModel):
    id: str
    title: str
    description: str
    location: str
    required_skills: list[str]


class InterviewCompetencyResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    associated_skill: str | None
    assessment_criteria: list[str]
    required_proficiency_level: int | None
    importance_weight: float | None
    mandatory: bool
    source: str
    candidate_evidence: str


class InterviewProficiencyLevelResponse(BaseModel):
    level: int
    name: str
    description: str


class InterviewCourseRecommendationResponse(BaseModel):
    course: TrainingCourseResponse
    matching_skills: list[str]
    reason: str


class CandidateInterviewPreparationProfileResponse(BaseModel):
    role: CandidateInterviewRoleResponse
    required_competencies: list[InterviewCompetencyResponse]
    suggested_competencies: list[InterviewCompetencyResponse]
    proficiency_levels: list[InterviewProficiencyLevelResponse]
    cv_evidence: CandidateProfileResponse | None = None
    recommended_courses: list[InterviewCourseRecommendationResponse] = Field(default_factory=list)


class TechnicalAssessmentStartRequest(BaseModel):
    offer_id: str = Field(min_length=1, max_length=36)
    skill: str = Field(min_length=1, max_length=60)

    @field_validator("offer_id", "skill")
    @classmethod
    def trim_assessment_target(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("An offer and skill are required.")
        return clean


class TechnicalAssessmentAnswerRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=20)
    answer: str | None = Field(default=None, max_length=10000)
    selected_option_id: str | None = Field(default=None, max_length=20)

    @field_validator("answer")
    @classmethod
    def trim_assessment_answer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        return clean or None

    @field_validator("selected_option_id")
    @classmethod
    def trim_option_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        return clean or None

    @model_validator(mode="after")
    def require_one_answer_format(self) -> "TechnicalAssessmentAnswerRequest":
        if (self.answer is None) == (self.selected_option_id is None):
            raise ValueError("Provide either a text answer or one selected option.")
        return self


class TechnicalAssessmentOptionResponse(BaseModel):
    id: str
    label: str


class TechnicalAssessmentCriterionResponse(BaseModel):
    id: str
    label: str


class TechnicalAssessmentQuestionResponse(BaseModel):
    id: str
    type: Literal["knowledge", "practical", "scenario"]
    format: Literal["multiple_choice", "short_answer", "text_exercise"]
    skill: str
    prompt: str
    options: list[TechnicalAssessmentOptionResponse] = Field(default_factory=list)
    criteria: list[TechnicalAssessmentCriterionResponse] = Field(default_factory=list)


class TechnicalAssessmentCriterionScoreResponse(BaseModel):
    criterion_id: str
    label: str
    score: int
    max_score: int


class TechnicalAssessmentEvaluationResponse(BaseModel):
    score: int
    max_score: int
    criteria_scores: list[TechnicalAssessmentCriterionScoreResponse]
    explanation: str
    strengths: list[str]
    weaknesses: list[str]
    suggested_improvements: list[str]
    method: Literal["deterministic", "llm"]


class TechnicalAssessmentAnswerResponse(BaseModel):
    question_id: str
    answer: str
    evaluation: TechnicalAssessmentEvaluationResponse
    created_at: datetime


class CandidateTechnicalAssessmentResponse(BaseModel):
    id: str
    offer_id: str
    offer_title: str
    skill: str
    status: Literal["in_progress", "completed"]
    questions: list[TechnicalAssessmentQuestionResponse]
    answers: list[TechnicalAssessmentAnswerResponse]
    created_at: datetime
    updated_at: datetime


class BehavioralAssessmentQuestionResponse(BaseModel):
    id: str
    type: Literal["behavioral", "situational"]
    format: Literal["star_text", "text_answer"]
    competency_id: str
    competency_name: str
    prompt: str
    criteria: list[TechnicalAssessmentCriterionResponse]
    star_components: list[TechnicalAssessmentCriterionResponse]


class BehavioralSTARScoreResponse(BaseModel):
    score: int
    max_score: int
    evidence: str


class BehavioralAssessmentEvaluationResponse(BaseModel):
    score: int
    max_score: int
    criteria_scores: list[TechnicalAssessmentCriterionScoreResponse]
    star_scores: dict[str, BehavioralSTARScoreResponse]
    explanation: str
    strengths: list[str]
    weaknesses: list[str]
    suggested_improvements: list[str]
    method: Literal["llm"]


class BehavioralAssessmentAnswerResponse(BaseModel):
    question_id: str
    answer: str
    evaluation: BehavioralAssessmentEvaluationResponse
    created_at: datetime


class CandidateBehavioralAssessmentResponse(BaseModel):
    id: str
    offer_id: str
    offer_title: str
    competency_id: str
    competency_name: str
    status: Literal["in_progress", "completed"]
    questions: list[BehavioralAssessmentQuestionResponse]
    answers: list[BehavioralAssessmentAnswerResponse]
    created_at: datetime
    updated_at: datetime


class CandidateInterviewTranscriptionResponse(BaseModel):
    id: str
    assessment_type: Literal["technical", "behavioral"]
    assessment_id: str
    question_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    transcript: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
