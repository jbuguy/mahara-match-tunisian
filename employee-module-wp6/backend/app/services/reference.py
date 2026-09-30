from sqlalchemy import String, case, cast, or_, select
from sqlalchemy.orm import Session

from app.models import Governorate, Occupation, Skill

SEARCH_LIMIT = 20


def _like(q: str) -> tuple[str, str]:
    """ILIKE patterns (contains, starts with) with the user's % and _ taken literally."""
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%", f"{escaped}%"


def list_governorates(db: Session) -> list[Governorate]:
    return list(db.scalars(select(Governorate).order_by(Governorate.code)))


def search_skills(db: Session, q: str) -> list[Skill]:
    """Validated skills whose label, code or alternative labels contain q; label prefix matches first."""
    statement = select(Skill).where(Skill.status == "validated")
    if q := q.strip():
        contains, prefix = _like(q)
        statement = statement.where(
            or_(
                Skill.label_fr.ilike(contains, escape="\\"),
                Skill.code.ilike(contains, escape="\\"),
                # alt_labels holds accent-free spellings too ("developpement web").
                cast(Skill.alt_labels, String).ilike(contains, escape="\\"),
            )
        ).order_by(case((Skill.label_fr.ilike(prefix, escape="\\"), 0), else_=1))
    return list(db.scalars(statement.order_by(Skill.label_fr).limit(SEARCH_LIMIT)))


def search_occupations(db: Session, q: str) -> list[Occupation]:
    statement = select(Occupation)
    if q := q.strip():
        contains, prefix = _like(q)
        statement = statement.where(
            or_(Occupation.title_fr.ilike(contains, escape="\\"), Occupation.code.ilike(contains, escape="\\"))
        ).order_by(case((Occupation.title_fr.ilike(prefix, escape="\\"), 0), else_=1))
    return list(db.scalars(statement.order_by(Occupation.title_fr).limit(SEARCH_LIMIT)))
