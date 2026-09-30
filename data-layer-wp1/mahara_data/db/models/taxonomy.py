"""Skills ontology and occupation referential (Taxonomie & Ontologie Skills)."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ... import enums as e
from .. import enum_types as t
from ..base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, CreatedAtMixin


class SkillCategory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "skill_categories"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name_fr: Mapped[str] = mapped_column(String(160), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(160))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("skill_categories.id"))


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skills"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    label_fr: Mapped[str] = mapped_column(String(200), nullable=False)
    label_ar: Mapped[str | None] = mapped_column(String(200))
    label_derja: Mapped[str | None] = mapped_column(String(200))
    # Synonyms in any language/script (FR, AR, Derja in Arabic or Latin script).
    alt_labels: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    skill_type: Mapped[e.SkillType] = mapped_column(t.skill_type, nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("skill_categories.id"))
    status: Mapped[e.TaxonomyStatus] = mapped_column(t.taxonomy_status, default=e.TaxonomyStatus.DRAFT, nullable=False)
    esco_uri: Mapped[str | None] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    validated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SkillRelation(Base):
    __tablename__ = "skill_relations"
    __table_args__ = (CheckConstraint("source_skill_id <> target_skill_id", name="skill_relations_no_self_ref"),)

    source_skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    target_skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    relation_type: Mapped[e.SkillRelationType] = mapped_column(t.skill_relation_type, primary_key=True)


class SkillSuggestion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Unknown skill labels found by the pipelines, waiting for admin review (WP5)."""

    __tablename__ = "skill_suggestions"

    proposed_label: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_label: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    skill_type: Mapped[e.SkillType | None] = mapped_column(t.skill_type)
    source: Mapped[e.IngestionSource] = mapped_column(t.ingestion_source, nullable=False)
    occurrences: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[e.SuggestionStatus] = mapped_column(
        t.suggestion_status, default=e.SuggestionStatus.PENDING, nullable=False
    )
    resolved_skill_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("skills.id"))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Occupation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Référentiel Métiers, aligned with ministry nomenclatures and ISCO-08."""

    __tablename__ = "occupations"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    isco_code: Mapped[str | None] = mapped_column(String(8))
    title_fr: Mapped[str] = mapped_column(String(200), nullable=False)
    title_ar: Mapped[str | None] = mapped_column(String(200))
    alt_titles: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sector_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sectors.id"))
    status: Mapped[e.TaxonomyStatus] = mapped_column(t.taxonomy_status, default=e.TaxonomyStatus.DRAFT, nullable=False)


class OccupationSkill(Base):
    __tablename__ = "occupation_skills"

    occupation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("occupations.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    requirement: Mapped[e.RequirementLevel] = mapped_column(t.requirement_level, nullable=False)
