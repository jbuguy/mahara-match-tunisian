import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mahara_data.db.models.taxonomy import Skill
from mahara_data.enums import SkillType, TaxonomyStatus
from mahara_data.schemas.taxonomy import SkillRead


from ..schemas import SkillCreate, SkillUpdate
from . import audit
from ..repositories import taxonomy as repository


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
    return repository.get_skill_by_code(db, code)


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
    repository.add_skill(db, skill)
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
    return repository.list_skills(
        db, status=status, skill_type=skill_type, search=search, page=page, page_size=page_size
    )


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


def validate_skill(db: Session, skill: Skill, actor_user_id: uuid.UUID | None = None) -> Skill:
    """Promote an entry to the official referential. The core governance act of WP5."""
    skill.status = TaxonomyStatus.VALIDATED
    skill.validated_at = datetime.now(timezone.utc)
    skill.validated_by = actor_user_id
    audit.record(
        db, "skill.validated", "skill", skill.code, {"version": skill.version},
        actor_user_id=actor_user_id,
    )
    db.commit()
    db.refresh(skill)
    return skill


def remove_skill(db: Session, skill: Skill, actor_user_id: uuid.UUID | None = None) -> str:
    """Delete a never-used draft for real; retire anything else from circulation."""
    if skill.status == TaxonomyStatus.DRAFT:
        code = skill.code
        try:
            db.delete(skill)
            audit.record(db, "skill.deleted", "skill", code, {"reason": "unused draft"}, actor_user_id=actor_user_id)
            db.commit()
            return "deleted"
        except IntegrityError:
            # Something already references it after all: keep the history.
            db.rollback()

    audit.record(
        db, "skill.deprecated", "skill", skill.code, {"previous_status": skill.status.value},
        actor_user_id=actor_user_id,
    )
    skill.status = TaxonomyStatus.DEPRECATED
    db.commit()
    return "deprecated"
