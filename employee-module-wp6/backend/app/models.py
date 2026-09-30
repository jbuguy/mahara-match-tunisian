"""SQLAlchemy models matching employee-module-wp6/db/schema.sql (the schema is the source of truth)."""

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, LargeBinary, SmallInteger, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, deferred, mapped_column

ONBOARDING_PATHS = ("cv_upload", "derja_detailed")
LITERACY_LEVELS = ("literate", "basic", "non_literate")
SKILL_TYPES = ("hard", "soft", "language")
SKILL_SOURCES = ("self_declared", "cv")
SKILL_STATUSES = ("draft", "validated", "deprecated")
USER_ROLES = ("candidate", "employer", "admin", "ministry", "training_provider")
EDUCATION_LEVELS = (
    "none", "primary", "lower_secondary", "baccalaureate",
    "vocational_cap", "vocational_btp", "vocational_bts",
    "licence", "master", "engineer", "doctorate",
)


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


class Governorate(Base):
    __tablename__ = "governorates"

    code: Mapped[str] = mapped_column(primary_key=True)
    name_fr: Mapped[str]
    name_ar: Mapped[str]


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(unique=True)
    label_fr: Mapped[str]
    alt_labels: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    skill_type: Mapped[str]
    status: Mapped[str | None]


class Occupation(Base):
    __tablename__ = "occupations"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(unique=True)
    title_fr: Mapped[str]


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(unique=True)
    role: Mapped[str] = mapped_column(server_default="candidate")
    preferred_language: Mapped[str] = mapped_column(server_default="fr")
    last_login_at: Mapped[datetime | None]


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    onboarding_path: Mapped[str]
    literacy_level: Mapped[str] = mapped_column(server_default="literate")
    governorate_code: Mapped[str | None] = mapped_column(ForeignKey("governorates.code"))
    education_level: Mapped[str | None]
    years_experience: Mapped[int | None]
    languages: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    summary: Mapped[str | None]
    available_from: Mapped[date | None]
    consent_version: Mapped[str | None]
    consent_given_at: Mapped[datetime | None]


class CandidatePii(Base):
    __tablename__ = "candidate_pii"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    full_name: Mapped[str | None]
    email: Mapped[str | None]
    phone: Mapped[str | None]
    # The candidate's own 256x256 JPEG (null = show the Google photo). Deferred: only the photo endpoint loads it.
    photo: Mapped[bytes | None] = deferred(mapped_column(LargeBinary))


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    level: Mapped[int] = mapped_column(SmallInteger)
    source: Mapped[str]
    confidence: Mapped[float | None]


class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"

    id: Mapped[uuid.UUID] = uuid_pk()
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"))
    job_title_raw: Mapped[str]
    employer_name: Mapped[str | None]
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    duration_months: Mapped[int | None]
    description: Mapped[str | None]


class CandidateEducation(Base):
    __tablename__ = "candidate_educations"

    id: Mapped[uuid.UUID] = uuid_pk()
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"))
    level: Mapped[str | None]
    field_of_study: Mapped[str | None]
    institution: Mapped[str | None]
    graduation_year: Mapped[int | None]


class CandidateDesiredOccupation(Base):
    __tablename__ = "candidate_desired_occupations"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    occupation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("occupations.id"), primary_key=True)
    priority: Mapped[int | None] = mapped_column(SmallInteger)
