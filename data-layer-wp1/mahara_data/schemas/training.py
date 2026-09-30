"""Training catalog and certifications (Organismes de formation -> Historique Acquis)."""

import uuid
from datetime import date

from pydantic import Field, model_validator

from ..enums import CourseModality, VerificationStatus
from .common import Contract, GovernorateCode, ProficiencyLevel, TaxonomyCode


class CourseSkill(Contract):
    skill_code: TaxonomyCode
    target_level: ProficiencyLevel


class TrainingCourseRecord(Contract):
    course_id: uuid.UUID | None = None
    provider_id: uuid.UUID
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    modality: CourseModality
    duration_hours: int | None = Field(default=None, ge=1, le=5000)
    cost_tnd: float | None = Field(default=None, ge=0)
    governorate_code: GovernorateCode | None = None
    language: str = Field(default="fr", max_length=8)
    certification_name: str | None = Field(default=None, max_length=200)
    skills: list[CourseSkill] = Field(min_length=1)
    external_ref: str | None = Field(default=None, max_length=64)


class CertificationRecord(Contract):
    candidate_id: uuid.UUID
    title: str = Field(min_length=2, max_length=200)
    training_course_id: uuid.UUID | None = None
    provider_id: uuid.UUID | None = None
    issued_on: date | None = None
    expires_on: date | None = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    document_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _dates(self) -> "CertificationRecord":
        if self.issued_on and self.expires_on and self.expires_on < self.issued_on:
            raise ValueError("expires_on must be after issued_on")
        return self
