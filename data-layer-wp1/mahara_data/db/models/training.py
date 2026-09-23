"""Training providers, course catalog and candidate certifications (Historique Acquis)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Numeric, SmallInteger, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ... import enums as e
from .. import enum_types as t
from ..base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class TrainingProvider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "training_providers"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)  # public | private | ngo
    accreditation_ref: Mapped[str | None] = mapped_column(String(64))
    governorate_code: Mapped[str | None] = mapped_column(String(8), ForeignKey("governorates.code"))
    website: Mapped[str | None] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))


class TrainingCourse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "training_courses"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_providers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    modality: Mapped[e.CourseModality] = mapped_column(t.course_modality, nullable=False)
    duration_hours: Mapped[int | None] = mapped_column(SmallInteger)
    cost_tnd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # 0 = free
    governorate_code: Mapped[str | None] = mapped_column(String(8), ForeignKey("governorates.code"))
    language: Mapped[str] = mapped_column(String(8), default="fr", nullable=False)
    certification_name: Mapped[str | None] = mapped_column(String(200))
    external_ref: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TrainingCourseSkill(Base):
    __tablename__ = "training_course_skills"
    __table_args__ = (CheckConstraint("target_level between 1 and 4", name="training_course_skills_level_range"),)

    training_course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_courses.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("skills.id"), primary_key=True)
    target_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class CandidateCertification(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "candidate_certifications"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    training_course_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("training_courses.id"))
    provider_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("training_providers.id"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    issued_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    verification_status: Mapped[e.VerificationStatus] = mapped_column(
        t.verification_status, default=e.VerificationStatus.PENDING, nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id"))
