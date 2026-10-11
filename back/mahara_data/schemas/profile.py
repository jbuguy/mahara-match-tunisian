"""Unified candidate profile: the single JSON every onboarding path converges to.

Producer: WP2 (Onboarding Agent). Consumers: WP1 (persistence), WP3, WP4, WP6.
The profile is PII-free by design; identity data travels separately in
`CandidateIdentity` and is never sent to the matching engine.
"""

import uuid
from datetime import date, datetime

from pydantic import Field, model_validator

from ..enums import (
    ConversationChannel,
    EducationLevel,
    LiteracyLevel,
    OnboardingPath,
    SkillSource,
    SkillType,
)
from .common import (
    SCHEMA_VERSION,
    Contract,
    GovernorateCode,
    LanguageSkill,
    Location,
    ProficiencyLevel,
    TaxonomyCode,
)


class ProfileSkill(Contract):
    # Resolved taxonomy code. Left empty when the label is unknown: WP1 then files
    # it as a skill_suggestion for admin review instead of dropping it.
    skill_code: TaxonomyCode | None = None
    label_raw: str | None = Field(default=None, max_length=200, description="Label as heard/read, any language")
    skill_type: SkillType
    level: ProficiencyLevel
    source: SkillSource
    confidence: float = Field(default=1.0, ge=0, le=1)

    @model_validator(mode="after")
    def _code_or_label(self) -> "ProfileSkill":
        if not self.skill_code and not self.label_raw:
            raise ValueError("A skill needs a skill_code or a label_raw")
        return self


class ProfileExperience(Contract):
    job_title_raw: str = Field(min_length=1, max_length=200)
    occupation_code: TaxonomyCode | None = None
    employer_name: str | None = Field(default=None, max_length=200)
    is_informal: bool = False
    start_date: date | None = None
    end_date: date | None = None
    duration_months: int | None = Field(default=None, ge=0, le=720)
    governorate_code: GovernorateCode | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _dates_in_order(self) -> "ProfileExperience":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class ProfileEducation(Contract):
    level: EducationLevel
    field_of_study: str | None = Field(default=None, max_length=200)
    institution: str | None = Field(default=None, max_length=200)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    country_code: str = Field(default="TN", min_length=2, max_length=2)


class Mobility(Contract):
    radius_km: int | None = Field(default=None, ge=0, le=1000)
    governorates: list[GovernorateCode] = Field(default_factory=list)


class CandidateProfile(Contract):
    schema_version: str = SCHEMA_VERSION
    candidate_id: uuid.UUID | None = Field(default=None, description="Null on first submission; assigned by WP1")
    onboarding_path: OnboardingPath
    literacy_level: LiteracyLevel
    preferred_language: str = Field(default="ar-TN", max_length=8)
    languages: list[LanguageSkill] = Field(default_factory=list)
    location: Location | None = None
    mobility: Mobility = Field(default_factory=Mobility)
    education_level: EducationLevel | None = None
    educations: list[ProfileEducation] = Field(default_factory=list)
    years_experience: float | None = Field(default=None, ge=0, le=60)
    experiences: list[ProfileExperience] = Field(default_factory=list)
    skills: list[ProfileSkill] = Field(default_factory=list)
    desired_occupation_codes: list[TaxonomyCode] = Field(default_factory=list, max_length=5)
    available_from: date | None = None
    summary: str | None = Field(default=None, max_length=2000)
    service_offer: str | None = Field(default=None, max_length=4000, description="Offre de service (derja_detailed)")
    source_document_ids: list[uuid.UUID] = Field(default_factory=list)
    conversation_session_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _path_consistency(self) -> "CandidateProfile":
        if self.onboarding_path is OnboardingPath.CV_UPLOAD and not self.source_document_ids:
            raise ValueError("cv_upload profiles must reference the uploaded CV in source_document_ids")
        if self.onboarding_path is not OnboardingPath.CV_UPLOAD and self.conversation_session_id is None:
            raise ValueError("Derja profiles must reference their conversation_session_id")
        if self.onboarding_path is OnboardingPath.DERJA_GUIDED_VOICE and self.literacy_level is LiteracyLevel.LITERATE:
            raise ValueError("derja_guided_voice is the path for non-literate candidates")
        codes = [s.skill_code for s in self.skills if s.skill_code]
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate skill_code in skills")
        return self


class CandidateIdentity(Contract):
    """PII, stored in candidate_pii. Readable by the candidate, and by an employer only after an application."""

    candidate_id: uuid.UUID
    full_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{8,15}$")
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=16)
    address: str | None = None


class AppetenceVector(Contract):
    """Structured output of a conversation (Vecteur d'Appétence), scores in [0, 1]."""

    conversation_session_id: uuid.UUID
    candidate_id: uuid.UUID | None = None
    channel: ConversationChannel
    detected_intents: list[str] = Field(default_factory=list)
    occupation_interests: dict[TaxonomyCode, float] = Field(default_factory=dict)
    sector_interests: dict[TaxonomyCode, float] = Field(default_factory=dict)
    computed_at: datetime

    @model_validator(mode="after")
    def _scores_in_unit_range(self) -> "AppetenceVector":
        for score in [*self.occupation_interests.values(), *self.sector_interests.values()]:
            if not 0 <= score <= 1:
                raise ValueError("Interest scores must be between 0 and 1")
        return self
