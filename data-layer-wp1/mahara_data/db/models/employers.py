"""Employers, normalized job offers, applications and hiring feedback (WP4/WP6)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ... import enums as e
from .. import enum_types as t
from ..base import Base, CreatedAtMixin, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class Employer(UUIDPrimaryKeyMixin, Base):
    """Superset of the WP4 `employers` table: the first 8 columns are WP4's, unchanged."""

    __tablename__ = "employers"

    company_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(120), nullable=False)
    company_size: Mapped[e.CompanySize] = mapped_column(t.company_size, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # WP1 additions
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), unique=True)
    sector_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sectors.id"))
    tax_id: Mapped[str | None] = mapped_column(String(32), unique=True)  # matricule fiscal
    governorate_code: Mapped[str | None] = mapped_column(String(8), ForeignKey("governorates.code"))
    website: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class JobOffer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Fiche Offre Normalisée."""

    __tablename__ = "job_offers"
    __table_args__ = (
        CheckConstraint("positions_count >= 1", name="job_offers_positions_positive"),
        CheckConstraint(
            "salary_min_tnd is null or salary_max_tnd is null or salary_min_tnd <= salary_max_tnd",
            name="job_offers_salary_range",
        ),
        Index("job_offers_status_governorate_idx", "status", "governorate_code"),
    )

    employer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employers.id", ondelete="CASCADE"), index=True
    )  # null for offers ingested from ministry feeds
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    description_normalized: Mapped[str | None] = mapped_column(Text)
    occupation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("occupations.id"))
    sector_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sectors.id"))
    contract_type: Mapped[e.ContractType] = mapped_column(t.contract_type, nullable=False)
    work_mode: Mapped[e.WorkMode] = mapped_column(t.work_mode, default=e.WorkMode.ON_SITE, nullable=False)
    governorate_code: Mapped[str] = mapped_column(String(8), ForeignKey("governorates.code"), nullable=False)
    delegation: Mapped[str | None] = mapped_column(String(80))
    positions_count: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    min_years_experience: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=Decimal("0"), nullable=False)
    education_level_min: Mapped[e.EducationLevel | None] = mapped_column(t.education_level)
    salary_min_tnd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    salary_max_tnd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    languages_required: Mapped[list[dict]] = mapped_column(JSONType, default=list, nullable=False)
    status: Mapped[e.OfferStatus] = mapped_column(t.offer_status, default=e.OfferStatus.DRAFT, nullable=False)
    source: Mapped[e.OfferSource] = mapped_column(t.offer_source, default=e.OfferSource.EMPLOYER_FORM, nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(64))
    # Result of the non-discrimination guardrail on the offer text.
    guardrail_flags: Mapped[list[dict]] = mapped_column(JSONType, default=list, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobOfferSkill(Base):
    __tablename__ = "job_offer_skills"
    __table_args__ = (CheckConstraint("min_level between 1 and 4", name="job_offer_skills_level_range"),)

    job_offer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_offers.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("skills.id"), primary_key=True)
    requirement: Mapped[e.RequirementLevel] = mapped_column(t.requirement_level, nullable=False)
    min_level: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)


class Application(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("candidate_id", "job_offer_id", name="applications_candidate_offer_key"),)

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_offer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_offers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Score snapshot at application time, so later re-scoring doesn't rewrite history.
    match_result_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("match_results.id"))
    status: Mapped[e.ApplicationStatus] = mapped_column(
        t.application_status, default=e.ApplicationStatus.SUBMITTED, nullable=False
    )
    cover_note: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class HiringFeedback(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Employer decision on an application; training signal for WP3, impact metric for WP5."""

    __tablename__ = "hiring_feedback"
    __table_args__ = (CheckConstraint("match_quality between 1 and 5", name="hiring_feedback_quality_range"),)

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("employers.id"), nullable=False)
    decision: Mapped[e.HiringDecision] = mapped_column(t.hiring_decision, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64))
    match_quality: Mapped[int | None] = mapped_column(SmallInteger)  # 1-5: how relevant was the suggested candidate
    comment: Mapped[str | None] = mapped_column(Text)
