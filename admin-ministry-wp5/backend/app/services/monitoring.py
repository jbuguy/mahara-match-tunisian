import time

from sqlalchemy import exists, func, select, text
from sqlalchemy.orm import Session

from mahara_data.db.models.taxonomy import Occupation, OccupationSkill, Skill, SkillSuggestion


def database_latency_ms(db: Session) -> float | None:
    """Round trip to the database. None means it could not be reached at all."""
    start = time.perf_counter()
    try:
        db.execute(text("select 1"))
    except Exception:
        db.rollback()
        return None
    return round((time.perf_counter() - start) * 1000, 2)


def _count_by_status(db: Session, model) -> dict[str, int]:
    rows = db.execute(select(model.status, func.count()).group_by(model.status)).all()
    return {getattr(value, "value", str(value)): count for value, count in rows}


def orphan_occupations(db: Session) -> int:
    """Validated occupations with no required skill: useless to WP3's gap detection."""
    has_no_skill = ~exists().where(OccupationSkill.occupation_id == Occupation.id)
    return db.execute(
        select(func.count()).select_from(Occupation).where(has_no_skill)
    ).scalar_one()


def taxonomy_counts(db: Session) -> dict:
    return {
        "skills": _count_by_status(db, Skill),
        "occupations": _count_by_status(db, Occupation),
        "suggestions": _count_by_status(db, SkillSuggestion),
        "occupations_without_skills": orphan_occupations(db),
    }