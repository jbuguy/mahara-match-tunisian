import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mahara_data.db.models.market import MarketDataset, MarketIndicator
from mahara_data.db.models.platform import IngestionJob
from mahara_data.db.models.reference import Governorate, Sector
from mahara_data.db.models.taxonomy import Occupation, Skill
from mahara_data.enums import IngestionSource, MarketDataOrigin, ProcessingStatus
from mahara_data.schemas.market import MarketIndicatorRecord

from ..schemas import MarketDatasetOut, MarketDatasetSubmission
from . import audit

# Bumped whenever the resolution rules change, so a job says which rules produced it.
PIPELINE_VERSION = "wp5-market-1.0"

# The referentials a ministry row may point at, and the column holding their code.
_LOOKUPS = {
    "skill": (Skill.id, Skill.code),
    "occupation": (Occupation.id, Occupation.code),
    "sector": (Sector.id, Sector.code),
    "governorate": (Governorate.code, Governorate.code),
}

_FIELDS = (
    ("skill", "skill_code", "skill_id"),
    ("occupation", "occupation_code", "occupation_id"),
    ("sector", "sector_code", "sector_id"),
    ("governorate", "governorate_code", "governorate_code"),
)


def _resolve_code(db: Session, cache: dict, kind: str, code: str):
    """One lookup per distinct code, reused across every row of the dataset."""
    key = (kind, code)
    if key not in cache:
        id_column, code_column = _LOOKUPS[kind]
        cache[key] = db.execute(
            select(id_column).where(code_column == code)
        ).scalar_one_or_none()
    return cache[key]


def _resolve_record(
    db: Session, cache: dict, record: MarketIndicatorRecord
) -> tuple[dict, str | None]:
    """Codes in, ids out. One unknown code rejects the row — never the dataset."""
    links = {
        "skill_id": None,
        "occupation_id": None,
        "sector_id": None,
        "governorate_code": None,
    }
    for kind, field, target in _FIELDS:
        code = getattr(record, field)
        if code is None:
            continue
        found = _resolve_code(db, cache, kind, code)
        if found is None:
            return {}, f"unknown {kind} code: {code}"
        links[target] = found
    return links, None


def ingest(
    db: Session, submission: MarketDatasetSubmission
) -> tuple[MarketDataset, IngestionJob, list[dict]]:
    """Record the deposit, keep every row that resolves, report the rest."""
    job = IngestionJob(
        source=IngestionSource.MINISTRY_MARKET,
        status=ProcessingStatus.PROCESSING,
        pipeline_version=PIPELINE_VERSION,
        records_total=len(submission.records),
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()  # the dataset needs the job's id

    dataset = MarketDataset(
        title=submission.dataset.title,
        origin=submission.dataset.origin,
        publisher=submission.dataset.publisher,
        period_start=submission.dataset.period_start,
        period_end=submission.dataset.period_end,
        document_id=submission.dataset.document_id,
        ingestion_job_id=job.id,
        # TODO: uploaded_by once authentication lands.
    )
    db.add(dataset)
    db.flush()

    cache: dict = {}
    rejections: list[dict] = []

    for index, record in enumerate(submission.records):
        links, reason = _resolve_record(db, cache, record)
        if reason is not None:
            rejections.append({"index": index, "reason": reason})
            continue
        db.add(
            MarketIndicator(
                dataset_id=dataset.id,
                indicator_type=record.indicator_type,
                period_start=record.period_start,
                period_end=record.period_end,
                value=record.value,
                unit=record.unit,
                extra=record.extra,
                **links,
            )
        )

    job.records_failed = len(rejections)
    job.records_ok = job.records_total - job.records_failed
    job.errors = rejections
    # Failed only when nothing at all could be kept: a partial deposit is still a deposit.
    job.status = (
        ProcessingStatus.FAILED
        if job.records_total and job.records_ok == 0
        else ProcessingStatus.COMPLETED
    )
    job.finished_at = datetime.now(timezone.utc)

    audit.record(
        db,
        "market.dataset_ingested",
        "market_dataset",
        str(dataset.id),
        {
            "publisher": dataset.publisher,
            "origin": dataset.origin.value,
            "records_ok": job.records_ok,
            "records_failed": job.records_failed,
        },
    )
    db.commit()
    db.refresh(dataset)
    db.refresh(job)
    return dataset, job, rejections


def to_read(db: Session, dataset: MarketDataset) -> MarketDatasetOut:
    count = db.execute(
        select(func.count())
        .select_from(MarketIndicator)
        .where(MarketIndicator.dataset_id == dataset.id)
    ).scalar_one()

    job_status = None
    if dataset.ingestion_job_id is not None:
        job_status = db.execute(
            select(IngestionJob.status).where(IngestionJob.id == dataset.ingestion_job_id)
        ).scalar_one_or_none()

    return MarketDatasetOut(
        dataset_id=dataset.id,
        title=dataset.title,
        origin=dataset.origin,
        publisher=dataset.publisher,
        period_start=dataset.period_start,
        period_end=dataset.period_end,
        indicator_count=count,
        job_id=dataset.ingestion_job_id,
        job_status=job_status,
    )


def get_dataset(db: Session, dataset_id: uuid.UUID) -> MarketDataset | None:
    return db.get(MarketDataset, dataset_id)


def list_datasets(
    db: Session,
    *,
    origin: MarketDataOrigin | None = None,
    publisher: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[MarketDataset], int]:
    """Most recent deposits first: that is what an admin checks after an upload."""
    stmt = select(MarketDataset)
    if origin is not None:
        stmt = stmt.where(MarketDataset.origin == origin)
    if publisher:
        stmt = stmt.where(MarketDataset.publisher.ilike(f"%{publisher.strip()}%"))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(MarketDataset.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).scalars().all()
    return list(rows), total