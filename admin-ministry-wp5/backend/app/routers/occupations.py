from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from mahara_data.db.models.taxonomy import Occupation
from mahara_data.enums import TaxonomyStatus
from mahara_data.schemas.common import Page
from mahara_data.schemas.taxonomy import OccupationRead

from ..db import get_db
from ..schemas import (
    OccupationCreate,
    OccupationSkillsReplace,
    OccupationUpdate,
    RemovalOut,
)
from ..services import occupations as service

router = APIRouter(prefix="/admin/taxonomy/occupations", tags=["admin-occupations"])


def _get_or_404(db: Session, code: str) -> Occupation:
    occupation = service.get_by_code(db, code)
    if occupation is None:
        raise HTTPException(status_code=404, detail=f"No occupation with code {code}")
    return occupation


def _sector_id_or_404(db: Session, code: str | None):
    """Codes come in, ids go to the database. The translation happens here."""
    if code is None:
        return None
    sector_id = service.sector_id_for(db, code)
    if sector_id is None:
        raise HTTPException(status_code=404, detail=f"No sector with code {code}")
    return sector_id


@router.post("", response_model=OccupationRead, status_code=status.HTTP_201_CREATED)
def create_occupation(
    payload: OccupationCreate, db: Annotated[Session, Depends(get_db)]
) -> OccupationRead:
    if service.get_by_code(db, payload.code) is not None:
        raise HTTPException(status_code=409, detail=f"Occupation code {payload.code} already exists")

    sector_id = _sector_id_or_404(db, payload.sector_code)
    return service.to_read(db, service.create_occupation(db, payload, sector_id))


@router.get("", response_model=Page[OccupationRead])
def list_occupations(
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[TaxonomyStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
) -> Page[OccupationRead]:
    rows, total = service.list_occupations(
        db, status=status_filter, search=search, page=page, page_size=page_size
    )
    return Page[OccupationRead](
        items=[service.to_read(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{code}", response_model=OccupationRead)
def read_occupation(code: str, db: Annotated[Session, Depends(get_db)]) -> OccupationRead:
    return service.to_read(db, _get_or_404(db, code))


@router.patch("/{code}", response_model=OccupationRead)
def edit_occupation(
    code: str, payload: OccupationUpdate, db: Annotated[Session, Depends(get_db)]
) -> OccupationRead:
    """Editorial corrections. Cannot change the status: see the dedicated routes."""
    occupation = _get_or_404(db, code)

    changes = payload.model_dump(exclude_unset=True)
    if "sector_code" in changes:
        changes["sector_id"] = _sector_id_or_404(db, changes.pop("sector_code"))

    return service.to_read(db, service.update_occupation(db, occupation, changes))


@router.post("/{code}/validate", response_model=OccupationRead)
def validate_occupation(code: str, db: Annotated[Session, Depends(get_db)]) -> OccupationRead:
    return service.to_read(db, service.validate_occupation(db, _get_or_404(db, code)))


@router.delete("/{code}", response_model=RemovalOut)
def remove_occupation(code: str, db: Annotated[Session, Depends(get_db)]) -> RemovalOut:
    """Deletes an unused draft, retires anything else. Never breaks existing offers."""
    occupation = _get_or_404(db, code)
    return RemovalOut(code=code, outcome=service.remove_occupation(db, occupation))


@router.put("/{code}/skills", response_model=OccupationRead)
def replace_required_skills(
    code: str, payload: OccupationSkillsReplace, db: Annotated[Session, Depends(get_db)]
) -> OccupationRead:
    """The complete requirement list. What you omit is removed."""
    occupation = _get_or_404(db, code)

    codes = [line.skill_code for line in payload.skills]
    duplicates = sorted({code for code in codes if codes.count(code) > 1})
    if duplicates:
        raise HTTPException(
            status_code=409, detail=f"Duplicate skill codes: {', '.join(duplicates)}"
        )

    pairs = []
    unknown = []
    for line in payload.skills:
        skill_id = service.skill_id_for(db, line.skill_code)
        if skill_id is None:
            unknown.append(line.skill_code)
        else:
            pairs.append((skill_id, line.requirement))

    # Report every bad code at once: the caller fixes one payload, not one code per round trip.
    if unknown:
        raise HTTPException(
            status_code=404, detail=f"Unknown skill codes: {', '.join(unknown)}"
        )

    return service.to_read(db, service.replace_skills(db, occupation, pairs))