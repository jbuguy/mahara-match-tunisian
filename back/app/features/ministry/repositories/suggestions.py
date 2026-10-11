import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mahara_data.db.models.taxonomy import Skill, SkillSuggestion
from mahara_data.enums import IngestionSource, SkillType, SuggestionStatus


def get_suggestion(db: Session, suggestion_id: uuid.UUID) -> SkillSuggestion | None:
    return db.get(SkillSuggestion, suggestion_id)


def get_resolved_skill_code(db: Session, skill_id: uuid.UUID) -> str | None:
    return db.execute(select(Skill.code).where(Skill.id == skill_id)).scalar_one_or_none()


def list_suggestions(
    db: Session,
    *,
    status: SuggestionStatus | None,
    source: IngestionSource | None,
    skill_type: SkillType | None,
    page: int,
    page_size: int,
) -> tuple[list[SkillSuggestion], int]:
    stmt = select(SkillSuggestion)
    if status is not None:
        stmt = stmt.where(SkillSuggestion.status == status)
    if source is not None:
        stmt = stmt.where(SkillSuggestion.source == source)
    if skill_type is not None:
        stmt = stmt.where(SkillSuggestion.skill_type == skill_type)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(SkillSuggestion.occurrences.desc(), SkillSuggestion.created_at)
        .limit(page_size).offset((page - 1) * page_size)
    ).scalars().all()
    return list(rows), total
