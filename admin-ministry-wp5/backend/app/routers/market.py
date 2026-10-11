import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from mahara_data.enums import MarketDataOrigin
from mahara_data.schemas.common import Page

from ..db import get_db
from ..schemas import IngestionReport, MarketDatasetOut, MarketDatasetSubmission, RecordRejection
from ..services import market as service

router = APIRouter(prefix="/admin/market", tags=["admin-market"])


@router.post("/datasets", response_model=IngestionReport, status_code=status.HTTP_201_CREATED)
def deposit_dataset(
    submission: MarketDatasetSubmission, db: Annotated[Session, Depends(get_db)]
) -> IngestionReport:
    """Ministry deposit. Valid rows are kept; rejected rows come back with their position."""
    dataset, job, rejections = service.ingest(db, submission)
    return IngestionReport(
        dataset_id=dataset.id,
        job_id=job.id,
        status=job.status,
        records_total=job.records_total,
        records_ok=job.records_ok,
        records_failed=job.records_failed,
        rejections=[RecordRejection(**item) for item in rejections],
    )


@router.get("/datasets", response_model=Page[MarketDatasetOut])
def list_datasets(
    db: Annotated[Session, Depends(get_db)],
    origin: MarketDataOrigin | None = None,
    publisher: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
) -> Page[MarketDatasetOut]:
    rows, total = service.list_datasets(
        db, origin=origin, publisher=publisher, page=page, page_size=page_size
    )
    return Page[MarketDatasetOut](
        items=[service.to_read(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/datasets/{dataset_id}", response_model=MarketDatasetOut)
def read_dataset(
    dataset_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> MarketDatasetOut:
    dataset = service.get_dataset(db, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"No dataset with id {dataset_id}")
    return service.to_read(db, dataset)