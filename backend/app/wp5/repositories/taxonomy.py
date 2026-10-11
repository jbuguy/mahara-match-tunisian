from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mahara_data.db.models.taxonomy import Skill
from mahara_data.enums import SkillType, TaxonomyStatus


def get_skill_by_code(db: Session, code: str) -> Skill | None:
    return db.execute(select(Skill).where(Skill.code == code)).scalar_one_or_none()


def list_skills(
    db: Session,
    *,
    status: TaxonomyStatus | None,
    skill_type: SkillType | None,
    search: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Skill], int]:
    stmt = select(Skill)
    if status is not None:
        stmt = stmt.where(Skill.status == status)
    if skill_type is not None:
        stmt = stmt.where(Skill.skill_type == skill_type)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(Skill.label_fr.ilike(pattern) | Skill.code.ilike(pattern))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Skill.code).limit(page_size).offset((page - 1) * page_size)).scalars().all()
    return list(rows), total


def add_skill(db: Session, skill: Skill) -> None:
    db.add(skill)

