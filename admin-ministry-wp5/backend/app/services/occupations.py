import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mahara_data.db.models.reference import Sector
from mahara_data.db.models.taxonomy import Occupation, OccupationSkill, Skill
from mahara_data.enums import RequirementLevel, TaxonomyStatus
from mahara_data.schemas.taxonomy import OccupationRead, OccupationSkillRead

from ..schemas import OccupationCreate


def to_read(db: Session, occupation: Occupation) -> OccupationRead:
    """Translate internal ids back into the codes other modules speak."""
    sector_code = None
    if occupation.sector_id is not None:
        sector_code = db.execute(
            select(Sector.code).where(Sector.id == occupation.sector_id)
        ).scalar_one_or_none()

    rows = db.execute(
        select(Skill.code, OccupationSkill.requirement)
        .join(OccupationSkill, OccupationSkill.skill_id == Skill.id)
        .where(OccupationSkill.occupation_id == occupation.id)
        .order_by(Skill.code)
    ).all()

    return OccupationRead(
        occupation_id=occupation.id,
        code=occupation.code,
        isco_code=occupation.isco_code,
        title_fr=occupation.title_fr,
        title_ar=occupation.title_ar,
        alt_titles=occupation.alt_titles,
        sector_code=sector_code,
        status=occupation.status,
        skills=[
            OccupationSkillRead(skill_code=code, requirement=requirement)
            for code, requirement in rows
        ],
    )


def get_by_code(db: Session, code: str) -> Occupation | None:
    return db.execute(select(Occupation).where(Occupation.code == code)).scalar_one_or_none()


def sector_id_for(db: Session, code: str) -> uuid.UUID | None:
    return db.execute(select(Sector.id).where(Sector.code == code)).scalar_one_or_none()


def skill_id_for(db: Session, code: str) -> uuid.UUID | None:
    return db.execute(select(Skill.id).where(Skill.code == code)).scalar_one_or_none()


def create_occupation(
    db: Session, payload: OccupationCreate, sector_id: uuid.UUID | None
) -> Occupation:
    """A new occupation always starts as a draft, like any entry of the referential."""
    occupation = Occupation(
        code=payload.code,
        isco_code=payload.isco_code,
        title_fr=payload.title_fr,
        title_ar=payload.title_ar,
        alt_titles=payload.alt_titles,
        description=payload.description,
        sector_id=sector_id,
        status=TaxonomyStatus.DRAFT,
    )
    db.add(occupation)
    db.commit()
    db.refresh(occupation)
    return occupation


def list_occupations(
    db: Session,
    *,
    status: TaxonomyStatus | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[Occupation], int]:
    stmt = select(Occupation)

    if status is not None:
        stmt = stmt.where(Occupation.status == status)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(Occupation.title_fr.ilike(pattern) | Occupation.code.ilike(pattern))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Occupation.code).limit(page_size).offset((page - 1) * page_size)
    ).scalars().all()
    return list(rows), total


def update_occupation(db: Session, occupation: Occupation, changes: dict) -> Occupation:
    """Changes arrive already translated: the router turned codes into ids."""
    if not changes:
        return occupation

    for field, value in changes.items():
        setattr(occupation, field, value)

    db.commit()
    db.refresh(occupation)
    return occupation


def validate_occupation(db: Session, occupation: Occupation) -> Occupation:
    """Promote the occupation to the official referential. A WP5 governance act."""
    occupation.status = TaxonomyStatus.VALIDATED
    db.commit()
    db.refresh(occupation)
    return occupation


def remove_occupation(db: Session, occupation: Occupation) -> str:
    """Delete a never-used draft for real; retire anything else from circulation."""
    if occupation.status == TaxonomyStatus.DRAFT:
        try:
            db.execute(
                delete(OccupationSkill).where(OccupationSkill.occupation_id == occupation.id)
            )
            db.delete(occupation)
            db.commit()
            return "deleted"
        except IntegrityError:
            db.rollback()

    occupation.status = TaxonomyStatus.DEPRECATED
    db.commit()
    return "deprecated"


def replace_skills(
    db: Session, occupation: Occupation, pairs: list[tuple[uuid.UUID, RequirementLevel]]
) -> Occupation:
    """Wipe and rewrite the requirement list, so the result is one coherent snapshot."""
    db.execute(delete(OccupationSkill).where(OccupationSkill.occupation_id == occupation.id))
    for skill_id, requirement in pairs:
        db.add(
            OccupationSkill(
                occupation_id=occupation.id, skill_id=skill_id, requirement=requirement
            )
        )
    db.commit()
    db.refresh(occupation)
    return occupation