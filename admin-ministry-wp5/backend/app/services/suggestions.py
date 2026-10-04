import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mahara_data.db.models.taxonomy import Skill, SkillSuggestion
from mahara_data.enums import IngestionSource, SkillType, SuggestionStatus, TaxonomyStatus
from mahara_data.schemas.taxonomy import SkillSuggestionRead

from ..schemas import SuggestionApprove
from . import audit


def to_read(db: Session, suggestion: SkillSuggestion) -> SkillSuggestionRead:
    """Map onto WP1's contract: callers see a taxonomy code, never an internal id."""
    resolved_code = None
    if suggestion.resolved_skill_id is not None:
        resolved_code = db.execute(
            select(Skill.code).where(Skill.id == suggestion.resolved_skill_id)
        ).scalar_one_or_none()

    return SkillSuggestionRead(
        suggestion_id=suggestion.id,
        proposed_label=suggestion.proposed_label,
        normalized_label=suggestion.normalized_label,
        skill_type=suggestion.skill_type,
        source=suggestion.source,
        occurrences=suggestion.occurrences,
        status=suggestion.status,
        resolved_skill_code=resolved_code,
    )


def get(db: Session, suggestion_id: uuid.UUID) -> SkillSuggestion | None:
    return db.get(SkillSuggestion, suggestion_id)


def list_suggestions(
    db: Session,
    *,
    status: SuggestionStatus | None = SuggestionStatus.PENDING,
    source: IngestionSource | None = None,
    skill_type: SkillType | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[SkillSuggestion], int]:
    """Busiest labels first: the admin reviews what blocks the most candidates."""
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
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).scalars().all()
    return list(rows), total


def _close(
    suggestion: SkillSuggestion,
    status: SuggestionStatus,
    skill_id: uuid.UUID | None = None,
) -> None:
    """Every verdict closes the suggestion the same way: status, link, timestamp."""
    suggestion.status = status
    suggestion.resolved_skill_id = skill_id
    suggestion.reviewed_at = datetime.now(timezone.utc)
    # TODO: set reviewed_by once authentication lands (users.id of the acting admin).


def approve(db: Session, suggestion: SkillSuggestion, payload: SuggestionApprove) -> Skill:
    """Create the skill this suggestion was asking for. A draft, like any new entry."""
    alt_labels = (
        [] if payload.label_fr == suggestion.proposed_label else [suggestion.proposed_label]
    )
    skill = Skill(
        code=payload.code,
        label_fr=payload.label_fr,
        label_ar=payload.label_ar,
        label_derja=payload.label_derja,
        alt_labels=alt_labels,
        description=payload.description,
        skill_type=payload.skill_type,
        status=TaxonomyStatus.DRAFT,
    )
    db.add(skill)
    db.flush()  # gets the new id without closing the transaction

    _close(suggestion, SuggestionStatus.APPROVED, skill.id)
    audit.record(
        db,
        "suggestion.approved",
        "skill_suggestion",
        str(suggestion.id),
        {"created_skill_code": skill.code, "proposed_label": suggestion.proposed_label},
    )
    db.commit()
    db.refresh(skill)
    return skill


def merge(db: Session, suggestion: SkillSuggestion, skill: Skill) -> Skill:
    """The label was a synonym. Keep it so the pipelines recognise it next time."""
    known = {skill.label_fr, *skill.alt_labels}
    if suggestion.proposed_label not in known:
        # Rebuild the list: an in-place append is invisible on a JSON column.
        skill.alt_labels = [*skill.alt_labels, suggestion.proposed_label]
        skill.version += 1

    _close(suggestion, SuggestionStatus.MERGED, skill.id)
    audit.record(
        db,
        "suggestion.merged",
        "skill_suggestion",
        str(suggestion.id),
        {"merged_into": skill.code, "proposed_label": suggestion.proposed_label},
    )
    db.commit()
    db.refresh(skill)
    return skill


def reject(db: Session, suggestion: SkillSuggestion) -> SkillSuggestion:
    """Noise. Traced, never deleted: a refusal is part of the governance history."""
    _close(suggestion, SuggestionStatus.REJECTED)
    audit.record(
        db,
        "suggestion.rejected",
        "skill_suggestion",
        str(suggestion.id),
        {"proposed_label": suggestion.proposed_label},
    )
    db.commit()
    db.refresh(suggestion)
    return suggestion