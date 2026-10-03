from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mahara_data.db.models.taxonomy import Skill
from mahara_data.enums import SkillType, TaxonomyStatus
from mahara_data.schemas.taxonomy import SkillRead

from ..schemas import SkillCreate, SkillUpdate


def to_read(skill: Skill) -> SkillRead:
    """Map the ORM row onto WP1's shared contract — the shape other modules expect."""
    return SkillRead(
        skill_id=skill.id,
        code=skill.code,
        label_fr=skill.label_fr,
        label_ar=skill.label_ar,
        label_derja=skill.label_derja,
        alt_labels=skill.alt_labels,
        skill_type=skill.skill_type,
        status=skill.status,
        esco_uri=skill.esco_uri,
        version=skill.version,
    )


def get_by_code(db: Session, code: str) -> Skill | None:
    return db.execute(select(Skill).where(Skill.code == code)).scalar_one_or_none()


def create_skill(db: Session, payload: SkillCreate) -> Skill:
    """A new entry always starts as a draft: creating and validating are two separate acts."""
    skill = Skill(
        code=payload.code,
        label_fr=payload.label_fr,
        label_ar=payload.label_ar,
        label_derja=payload.label_derja,
        alt_labels=payload.alt_labels,
        description=payload.description,
        skill_type=payload.skill_type,
        status=TaxonomyStatus.DRAFT,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def list_skills(
    db: Session,
    *,
    status: TaxonomyStatus | None = None,
    skill_type: SkillType | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
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
    rows = db.execute(
        stmt.order_by(Skill.code).limit(page_size).offset((page - 1) * page_size)
    ).scalars().all()
    return list(rows), total


def update_skill(db: Session, skill: Skill, payload: SkillUpdate) -> Skill:
    """Apply editorial changes and bump the version: a shared referential tracks its edits."""
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return skill

    for field, value in changes.items():
        setattr(skill, field, value)
    skill.version += 1

    db.commit()
    db.refresh(skill)
    return skill


def validate_skill(db: Session, skill: Skill) -> Skill:
    """Promote an entry to the official referential. The core governance act of WP5."""
    skill.status = TaxonomyStatus.VALIDATED
    skill.validated_at = datetime.now(timezone.utc)
    # TODO: set validated_by once authentication lands (users.id of the acting admin).
    db.commit()
    db.refresh(skill)
    return skill


def remove_skill(db: Session, skill: Skill) -> str:
    """Delete a never-used draft for real; retire anything else from circulation."""
    if skill.status == TaxonomyStatus.DRAFT:
        try:
            db.delete(skill)
            db.commit()
            return "deleted"
        except IntegrityError:
            # Something already references it after all: keep the history.
            db.rollback()

    skill.status = TaxonomyStatus.DEPRECATED
    db.commit()
    return "deprecated"