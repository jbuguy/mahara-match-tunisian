from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from mahara_data.db.models.taxonomy import Skill
from mahara_data.enums import SkillType, TaxonomyStatus
from mahara_data.schemas.common import Page
from mahara_data.schemas.taxonomy import SkillRead


from ..db import get_db
from ..schemas import RemovalOut, SkillCreate, SkillUpdate
from ..services import taxonomy as service

router = APIRouter(prefix="/admin/taxonomy", tags=["admin-taxonomy"])


def _get_or_404(db: Session, code: str) -> Skill:
    skill = service.get_by_code(db, code)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"No skill with code {code}")
    return skill


@router.post("/skills", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(payload: SkillCreate, db: Annotated[Session, Depends(get_db)]) -> SkillRead:
    if service.get_by_code(db, payload.code) is not None:
        raise HTTPException(status_code=409, detail=f"Skill code {payload.code} already exists")
    return service.to_read(service.create_skill(db, payload))


@router.get("/skills", response_model=Page[SkillRead])
def list_skills(
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[TaxonomyStatus | None, Query(alias="status")] = None,
    skill_type: SkillType | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
) -> Page[SkillRead]:
    rows, total = service.list_skills(
        db,
        status=status_filter,
        skill_type=skill_type,
        search=search,
        page=page,
        page_size=page_size,
    )
    return Page[SkillRead](
        items=[service.to_read(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/skills/{code}", response_model=SkillRead)
def read_skill(code: str, db: Annotated[Session, Depends(get_db)]) -> SkillRead:
    return service.to_read(_get_or_404(db, code))


@router.patch("/skills/{code}", response_model=SkillRead)
def edit_skill(
    code: str, payload: SkillUpdate, db: Annotated[Session, Depends(get_db)]
) -> SkillRead:
    """Editorial corrections. Cannot change the status: see the dedicated routes."""
    return service.to_read(service.update_skill(db, _get_or_404(db, code), payload))


@router.post("/skills/{code}/validate", response_model=SkillRead)
def validate_skill(code: str, db: Annotated[Session, Depends(get_db)]) -> SkillRead:
    return service.to_read(service.validate_skill(db, _get_or_404(db, code)))


@router.delete("/skills/{code}", response_model=RemovalOut)
def remove_skill(code: str, db: Annotated[Session, Depends(get_db)]) -> RemovalOut:
    """Deletes an unused draft, retires anything else. Never breaks existing profiles."""
    skill = _get_or_404(db, code)
    return RemovalOut(code=code, outcome=service.remove_skill(db, skill))