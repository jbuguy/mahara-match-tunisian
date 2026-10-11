"""Validated lookups and searches for WP1 reference data and taxonomy."""

from collections.abc import Sequence

from sqlalchemy import String, case, cast, or_, select
from sqlalchemy.orm import Session

from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Occupation, Skill
from mahara_data.enums import TaxonomyStatus


def list_validated_skills(db: Session) -> list[Skill]:
    return list(db.scalars(select(Skill).where(Skill.status == TaxonomyStatus.VALIDATED)))


def get_validated_skills_by_codes(db: Session, codes: Sequence[str]) -> list[Skill]:
    if not codes:
        return []
    return list(
        db.scalars(
            select(Skill).where(
                Skill.code.in_(set(codes)),
                Skill.status == TaxonomyStatus.VALIDATED,
            )
        )
    )


def get_skills_by_codes(db: Session, codes: Sequence[str]) -> list[Skill]:
    if not codes:
        return []
    return list(db.scalars(select(Skill).where(Skill.code.in_(set(codes)))))


def list_governorates(db: Session) -> list[Governorate]:
    return list(db.scalars(select(Governorate).order_by(Governorate.code)))


def search_skills(db: Session, query: str, *, limit: int = 20) -> list[Skill]:
    statement = select(Skill).where(Skill.status == TaxonomyStatus.VALIDATED)
    if query := query.strip():
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        contains, prefix = f"%{escaped}%", f"{escaped}%"
        statement = statement.where(
            or_(
                Skill.label_fr.ilike(contains, escape="\\"),
                Skill.code.ilike(contains, escape="\\"),
                cast(Skill.alt_labels, String).ilike(contains, escape="\\"),
            )
        ).order_by(case((Skill.label_fr.ilike(prefix, escape="\\"), 0), else_=1))
    return list(db.scalars(statement.order_by(Skill.label_fr).limit(limit)))


def search_occupations(db: Session, query: str, *, limit: int = 20) -> list[Occupation]:
    statement = select(Occupation)
    if query := query.strip():
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        contains, prefix = f"%{escaped}%", f"{escaped}%"
        statement = statement.where(
            or_(
                Occupation.title_fr.ilike(contains, escape="\\"),
                Occupation.code.ilike(contains, escape="\\"),
            )
        ).order_by(case((Occupation.title_fr.ilike(prefix, escape="\\"), 0), else_=1))
    return list(db.scalars(statement.order_by(Occupation.title_fr).limit(limit)))