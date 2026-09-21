"""Candidate profile (output of WP2, read by WP3/WP4/WP6).

PII lives in `candidate_pii`, a separate table with stricter access, so that
matching (WP3) can read the full profile without ever seeing name, gender or age.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ... import enums as e
from .. import enum_types as t
from ..base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class Candidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidates"
    __table_args__ = (
        CheckConstraint("profile_completeness between 0 and 100", name="candidates_completeness_range"),
        CheckConstraint("years_experience >= 0", name="candidates_years_experience_positive"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), unique=True)
    onboarding_path: Mapped[e.OnboardingPath] = mapped_column(t.onboarding_path, nullable=False)
    literacy_level: Mapped[e.LiteracyLevel] = mapped_column(t.literacy_level, nullable=False)
    governorate_code: Mapped[str | None] = mapped_column(String(8), ForeignKey("governorates.code"))
    delegation: Mapped[str | None] = mapped_column(String(80))
    mobility_radius_km: Mapped[int | None] = mapped_column(SmallInteger)
    mobility_governorates: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    education_level: Mapped[e.EducationLevel | None] = mapped_column(t.education_level)
    years_experience: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    # [{"code": "fr", "level": 3}, ...] using the 1-4 proficiency scale.
    languages: Mapped[list[dict]] = mapped_column(JSONType, default=list, nullable=False)
    available_from: Mapped[date | None] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)
    # "Offre de service" generated for literate candidates without a CV.
    service_offer: Mapped[str | None] = mapped_column(Text)
    profile_completeness: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Last unified profile JSON received from WP2, kept for traceability/replay.
    raw_profile: Mapped[dict | None] = mapped_column(JSONType)
    consent_version: Mapped[str | None] = mapped_column(String(16))
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CandidatePII(TimestampMixin, Base):
    __tablename__ = "candidate_pii"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    full_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(20))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(16))
    address: Mapped[str | None] = mapped_column(Text)


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (
        CheckConstraint("level between 1 and 4", name="candidate_skills_level_range"),
        CheckConstraint("confidence between 0 and 1", name="candidate_skills_confidence_range"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("skills.id"), primary_key=True)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    source: Mapped[e.SkillSource] = mapped_column(t.skill_source, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("1.00"), nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text)  # redacted snippet that justified the extraction


class CandidateExperience(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "candidate_experiences"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    occupation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("occupations.id"))
    job_title_raw: Mapped[str] = mapped_column(String(200), nullable=False)
    employer_name: Mapped[str | None] = mapped_column(String(200))
    is_informal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    # For oral profiles ("5 ans maçon") where exact dates are unknown.
    duration_months: Mapped[int | None] = mapped_column(SmallInteger)
    governorate_code: Mapped[str | None] = mapped_column(String(8), ForeignKey("governorates.code"))
    description: Mapped[str | None] = mapped_column(Text)


class CandidateEducation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "candidate_educations"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    level: Mapped[e.EducationLevel] = mapped_column(t.education_level, nullable=False)
    field_of_study: Mapped[str | None] = mapped_column(String(200))
    institution: Mapped[str | None] = mapped_column(String(200))
    graduation_year: Mapped[int | None] = mapped_column(SmallInteger)
    country_code: Mapped[str] = mapped_column(String(2), default="TN", nullable=False)


class CandidateDesiredOccupation(Base):
    __tablename__ = "candidate_desired_occupations"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    occupation_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("occupations.id"), primary_key=True)
    priority: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)


class ConversationSession(UUIDPrimaryKeyMixin, Base):
    """A WP2 onboarding dialogue; its output is the "vecteur d'appétence"."""

    __tablename__ = "conversation_sessions"

    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[e.ConversationChannel] = mapped_column(t.conversation_channel, nullable=False)
    onboarding_path: Mapped[e.OnboardingPath] = mapped_column(t.onboarding_path, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="ar-TN", nullable=False)
    status: Mapped[e.ProcessingStatus] = mapped_column(
        t.processing_status, default=e.ProcessingStatus.PENDING, nullable=False
    )
    # [{"role": "bot"|"user", "text": "...", "intent": "...", "at": "..."}], PII-redacted.
    transcript: Mapped[list[dict]] = mapped_column(JSONType, default=list, nullable=False)
    detected_intents: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    # {"occupations": {"<code>": 0.8}, "sectors": {"<code>": 0.6}}
    appetence: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
