"""Matching outputs written by WP3: scores, skill gaps and learning roadmaps."""

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
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ... import enums as e
from .. import enum_types as t
from ..base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin

_SCORE_COLUMNS = ("score_global", "score_hard_skills", "score_experience", "score_soft_skills", "score_location")


class MatchResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "match_results"
    __table_args__ = (
        *(CheckConstraint(f"{col} between 0 and 100", name=f"match_results_{col}_range") for col in _SCORE_COLUMNS),
        UniqueConstraint("candidate_id", "job_offer_id", "model_version", name="match_results_pair_version_key"),
        Index("match_results_candidate_score_idx", "candidate_id", "score_global"),
        Index("match_results_offer_score_idx", "job_offer_id", "score_global"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    job_offer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False
    )
    score_global: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    score_hard_skills: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    score_experience: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    score_soft_skills: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    score_location: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    weights: Mapped[dict] = mapped_column(JSONType, nullable=False)  # snapshot of the weights used
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SkillGap(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "skill_gaps"
    __table_args__ = (UniqueConstraint("match_result_id", "skill_id", name="skill_gaps_match_skill_key"),)

    match_result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("match_results.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("skills.id"), nullable=False)
    gap_type: Mapped[e.GapType] = mapped_column(t.gap_type, nullable=False)
    requirement: Mapped[e.RequirementLevel] = mapped_column(t.requirement_level, nullable=False)
    required_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    current_level: Mapped[int | None] = mapped_column(SmallInteger)  # null when gap_type = missing


class Roadmap(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roadmaps"
    __table_args__ = (
        CheckConstraint(
            "target_job_offer_id is not null or target_occupation_id is not null", name="roadmaps_target_required"
        ),
        CheckConstraint("progress_pct between 0 and 100", name="roadmaps_progress_range"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_job_offer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("job_offers.id", ondelete="SET NULL")
    )
    target_occupation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("occupations.id"))
    status: Mapped[e.RoadmapStatus] = mapped_column(t.roadmap_status, default=e.RoadmapStatus.ACTIVE, nullable=False)
    progress_pct: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)


class RoadmapItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "roadmap_items"
    __table_args__ = (UniqueConstraint("roadmap_id", "position", name="roadmap_items_position_key"),)

    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("skills.id"), nullable=False)
    training_course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_courses.id", ondelete="SET NULL")
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[e.RoadmapItemStatus] = mapped_column(
        t.roadmap_item_status, default=e.RoadmapItemStatus.TODO, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
