import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.models import EDUCATION_LEVELS, LITERACY_LEVELS, SKILL_SOURCES

EducationLevel = Literal[*EDUCATION_LEVELS]
LiteracyLevel = Literal[*LITERACY_LEVELS]
SkillSource = Literal[*SKILL_SOURCES]
# Stored in candidates.languages as [{code, level}]; code is ISO 639-1 (ar, fr, en...).
LANGUAGE_LEVELS = ("basic", "intermediate", "fluent", "native")
LanguageLevel = Literal[*LANGUAGE_LEVELS]

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Code = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class Me(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    has_profile: bool


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

class GovernorateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name_fr: str
    name_ar: str


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label_fr: str
    skill_type: str


class OccupationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    title_fr: str


# ---------------------------------------------------------------------------
# Profile: PUT /me/profile body
# ---------------------------------------------------------------------------

class LanguageIn(BaseModel):
    code: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, pattern=r"^[a-z]{2,3}$")]
    level: LanguageLevel


class SkillIn(BaseModel):
    code: Code
    level: int = Field(ge=1, le=4)
    source: SkillSource = "self_declared"
    confidence: float | None = Field(default=None, ge=0, le=1)


class ExperienceIn(BaseModel):
    job_title_raw: Text
    employer_name: Text | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_months: int | None = Field(default=None, ge=0)
    description: LongText | None = None

    @model_validator(mode="after")
    def end_after_start(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date is before start_date")
        return self


class EducationIn(BaseModel):
    level: EducationLevel | None = None
    field_of_study: Text | None = None
    institution: Text | None = None
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)


class DesiredOccupationIn(BaseModel):
    code: Code
    priority: int | None = Field(default=None, ge=1, le=32767)


def _no_duplicates(items: list, key: str, what: str) -> list:
    seen = [getattr(item, key) for item in items]
    duplicates = sorted({value for value in seen if seen.count(value) > 1})
    if duplicates:
        raise ValueError(f"duplicate {what}: {', '.join(duplicates)}")
    return items


class ProfileIn(BaseModel):
    """Everything the profile form sends. Saving replaces the whole profile."""

    consent: bool
    from_cv: bool = False  # True when the form was prefilled by a CV import → onboarding_path 'cv_upload'

    full_name: Text
    email: Annotated[str, StringConstraints(
        strip_whitespace=True, to_lower=True, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )] | None = None  # defaults to the login email
    phone: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9 ().-]{6,30}$")] | None = None

    governorate_code: Code | None = None
    literacy_level: LiteracyLevel | None = None  # new profiles default to 'literate'
    education_level: EducationLevel | None = None
    years_experience: int | None = Field(default=None, ge=0, le=80)
    languages: list[LanguageIn] = Field(default_factory=list, max_length=20)
    summary: LongText | None = None
    available_from: date | None = None

    skills: list[SkillIn] = Field(default_factory=list, max_length=100)
    experiences: list[ExperienceIn] = Field(default_factory=list, max_length=50)
    educations: list[EducationIn] = Field(default_factory=list, max_length=20)
    desired_occupations: list[DesiredOccupationIn] = Field(default_factory=list, max_length=10)

    @field_validator("consent")
    @classmethod
    def consent_given(cls, value: bool) -> bool:
        if not value:
            raise ValueError("consent is required")
        return value

    @field_validator("languages")
    @classmethod
    def unique_languages(cls, value: list[LanguageIn]) -> list[LanguageIn]:
        return _no_duplicates(value, "code", "language code")

    @field_validator("skills")
    @classmethod
    def unique_skills(cls, value: list[SkillIn]) -> list[SkillIn]:
        return _no_duplicates(value, "code", "skill code")

    @field_validator("desired_occupations")
    @classmethod
    def unique_occupations(cls, value: list[DesiredOccupationIn]) -> list[DesiredOccupationIn]:
        return _no_duplicates(value, "code", "occupation code")


# ---------------------------------------------------------------------------
# Profile: GET/PUT /me/profile response
# ---------------------------------------------------------------------------

class LanguageOut(BaseModel):
    code: str
    level: str


class ProfileSkillOut(BaseModel):
    code: str
    label_fr: str
    skill_type: str
    level: int
    source: str
    confidence: float | None


class ExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_title_raw: str
    employer_name: str | None
    start_date: date | None
    end_date: date | None
    duration_months: int | None
    description: str | None


class EducationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    level: str | None
    field_of_study: str | None
    institution: str | None
    graduation_year: int | None


class ProfileOccupationOut(BaseModel):
    code: str
    title_fr: str
    priority: int | None


class ProfileOut(BaseModel):
    full_name: str | None
    email: str | None
    phone: str | None
    has_photo: bool  # an uploaded photo exists (GET /me/photo); otherwise the UI shows the Google photo

    onboarding_path: str
    literacy_level: str
    governorate: GovernorateOut | None
    education_level: str | None
    years_experience: int | None
    languages: list[LanguageOut]
    summary: str | None
    available_from: date | None
    consent_version: str | None
    consent_given_at: datetime | None

    skills: list[ProfileSkillOut]
    experiences: list[ExperienceOut]
    educations: list[EducationOut]
    desired_occupations: list[ProfileOccupationOut]


# ---------------------------------------------------------------------------
# CV import: POST /me/cv response, in the profile form's own shape ('' = not found)
# ---------------------------------------------------------------------------

class CvSkill(BaseModel):
    code: str
    label_fr: str
    level: int = 2
    source: SkillSource = "cv"
    confidence: float | None = None


class CvExperience(BaseModel):
    job_title_raw: str
    employer_name: str = ""
    start_date: str = ""  # YYYY-MM-DD
    end_date: str = ""
    duration_months: str = ""
    description: str = ""


class CvEducation(BaseModel):
    """Same as EducationIn: the form sends educations back unchanged."""

    level: EducationLevel | None = None
    field_of_study: str | None = None
    institution: str | None = None
    graduation_year: int | None = None


class CvDraft(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    education_level: EducationLevel | Literal[""] = ""
    skills: list[CvSkill] = Field(default_factory=list)
    experiences: list[CvExperience] = Field(default_factory=list)
    educations: list[CvEducation] = Field(default_factory=list)


class CvImportOut(BaseModel):
    draft: CvDraft
    unmatched_words: list[str]  # items of the CV's Compétences / Langues sections that match no known skill


# ---------------------------------------------------------------------------
# Profile assistant: POST /me/assistant/chat (nothing is saved)
# ---------------------------------------------------------------------------

DraftText = Annotated[str, StringConstraints(max_length=5000)]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class DraftSkill(BaseModel):
    code: DraftText = ""
    label_fr: DraftText = ""
    level: int | None = None


class DraftExperience(BaseModel):
    job_title_raw: DraftText = ""
    employer_name: DraftText = ""
    start_date: DraftText = ""
    end_date: DraftText = ""
    duration_months: DraftText = ""


class DraftOccupation(BaseModel):
    code: DraftText = ""
    title_fr: DraftText = ""


class DraftLanguage(BaseModel):
    code: DraftText = ""
    level: DraftText = ""


class AssistantDraft(BaseModel):
    """The profile form as it is now. The frontend sends its form values; keys not listed here are ignored."""

    full_name: DraftText = ""
    phone: DraftText = ""
    governorate_code: DraftText = ""
    education_level: DraftText = ""
    skills: list[DraftSkill] = Field(default_factory=list, max_length=100)
    experiences: list[DraftExperience] = Field(default_factory=list, max_length=50)
    desired_occupations: list[DraftOccupation] = Field(default_factory=list, max_length=10)
    languages: list[DraftLanguage] = Field(default_factory=list, max_length=20)
    summary: DraftText = ""


class AssistantChatIn(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)  # only the last 8 go to the model
    draft: AssistantDraft = Field(default_factory=AssistantDraft)


class AssistantUpdates(BaseModel):
    """Fields to merge into the form, in its own shape (like the CV draft). A field left out is unchanged."""

    full_name: str | None = None
    phone: str | None = None
    governorate_code: str | None = None
    education_level: EducationLevel | None = None
    skills: list[CvSkill] | None = None
    experiences: list[CvExperience] | None = None
    desired_occupations: list[OccupationOut] | None = None
    languages: list[LanguageOut] | None = None
    summary: str | None = None


class AssistantChatOut(BaseModel):
    reply: str
    updates: AssistantUpdates
    unmatched: list[str]  # skills and jobs the candidate named that aren't in our lists
    # When something didn't match: close items of our lists the candidate can pick instead (labels).
    suggestions: list[str] = []
    # The form field the reply asks about (full_name, governorate_code, skills...), so the form can show it.
    asking: str | None = None
    done: bool


class TranscriptOut(BaseModel):
    text: str  # what the candidate said ('' when nothing was understood); goes into the chat's text box
