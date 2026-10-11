import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from mahara_data.db.models.taxonomy import Skill, SkillSuggestion
from mahara_data.enums import IngestionSource, SkillType, SuggestionStatus, TaxonomyStatus
from mahara_data.schemas.common import Page
from mahara_data.schemas.taxonomy import SkillRead, SkillSuggestionRead

from ..db import get_db
from ..schemas import SuggestionApprove, SuggestionMerge
from ..services import suggestions as service
from ..services import taxonomy as taxonomy_service

router = APIRouter(prefix="/admin/taxonomy/suggestions", tags=["admin-suggestions"])


def _pending_or_error(db: Session, suggestion_id: uuid.UUID) -> SkillSuggestion:
    """A verdict applies once. Re-reviewing a closed suggestion is a conflict, not a 404."""
    suggestion = service.get(db, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail=f"No suggestion with id {suggestion_id}")
    if suggestion.status != SuggestionStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"Suggestion already reviewed: {suggestion.status.value}",
        )
    return suggestion


def _target_skill(db: Session, code: str) -> Skill:
    """The skill a suggestion is merged into. It must exist and still be in circulation."""
    skill = taxonomy_service.get_by_code(db, code)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"No skill with code {code}")
    if skill.status == TaxonomyStatus.DEPRECATED:
        raise HTTPException(
            status_code=409, detail=f"Skill {code} is deprecated: pick a live entry"
        )
    return skill


@router.get("", response_model=Page[SkillSuggestionRead])
def list_suggestions(
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[
        SuggestionStatus | None, Query(alias="status")
    ] = SuggestionStatus.PENDING,
    source: IngestionSource | None = None,
    skill_type: SkillType | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
) -> Page[SkillSuggestionRead]:
    """The review inbox. Defaults to what is still waiting, busiest labels first."""
    rows, total = service.list_suggestions(
        db,
        status=status_filter,
        source=source,
        skill_type=skill_type,
        page=page,
        page_size=page_size,
    )
    return Page[SkillSuggestionRead](
        items=[service.to_read(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{suggestion_id}/approve", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def approve_suggestion(
    suggestion_id: uuid.UUID,
    payload: SuggestionApprove,
    db: Annotated[Session, Depends(get_db)],
) -> SkillRead:
    """The label was genuinely new. Creates the entry as a draft, to be validated separately."""
    suggestion = _pending_or_error(db, suggestion_id)
    if taxonomy_service.get_by_code(db, payload.code) is not None:
        raise HTTPException(status_code=409, detail=f"Skill code {payload.code} already exists")
    return taxonomy_service.to_read(service.approve(db, suggestion, payload))


@router.post("/{suggestion_id}/merge", response_model=SkillRead)
def merge_suggestion(
    suggestion_id: uuid.UUID,
    payload: SuggestionMerge,
    db: Annotated[Session, Depends(get_db)],
) -> SkillRead:
    """The label was a synonym. Enriches an existing entry instead of duplicating it."""
    suggestion = _pending_or_error(db, suggestion_id)
    return taxonomy_service.to_read(service.merge(db, suggestion, _target_skill(db, payload.code)))


@router.post("/{suggestion_id}/reject", response_model=SkillSuggestionRead)
def reject_suggestion(
    suggestion_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> SkillSuggestionRead:
    """Noise, typo, or not a skill. The refusal is recorded, never erased."""
    suggestion = _pending_or_error(db, suggestion_id)
    return service.to_read(db, service.reject(db, suggestion))