import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from mahara_data.enums import IngestionSource, ProcessingStatus
from mahara_data.schemas.common import Page

from ..db import get_db
from ..schemas import IngestionJobOut
from ..services import ingestion as service

router = APIRouter(prefix="/admin/ingestion", tags=["admin-ingestion"])


@router.get("/jobs", response_model=Page[IngestionJobOut])
def list_jobs(
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[ProcessingStatus | None, Query(alias="status")] = None,
    source: IngestionSource | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
) -> Page[IngestionJobOut]:
    """Every run of every pipeline, whatever module triggered it."""
    rows, total = service.list_jobs(
        db, status=status_filter, source=source, page=page, page_size=page_size
    )
    return Page[IngestionJobOut](
        items=[service.to_read(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/{job_id}", response_model=IngestionJobOut)
def read_job(job_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> IngestionJobOut:
    """The full report, rejected rows included."""
    job = service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No ingestion job with id {job_id}")
    return service.to_read(job)