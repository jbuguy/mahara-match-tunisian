import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mahara_data.db.models.platform import IngestionJob
from mahara_data.enums import IngestionSource, ProcessingStatus

from ..schemas import IngestionJobOut


def to_read(job: IngestionJob) -> IngestionJobOut:
    return IngestionJobOut(
        job_id=job.id,
        source=job.source,
        status=job.status,
        pipeline_version=job.pipeline_version,
        records_total=job.records_total,
        records_ok=job.records_ok,
        records_failed=job.records_failed,
        errors=job.errors,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
    )


def get_job(db: Session, job_id: uuid.UUID) -> IngestionJob | None:
    return db.get(IngestionJob, job_id)


def list_jobs(
    db: Session,
    *,
    status: ProcessingStatus | None = None,
    source: IngestionSource | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[IngestionJob], int]:
    """Most recent first: a run is checked right after it happens."""
    stmt = select(IngestionJob)
    if status is not None:
        stmt = stmt.where(IngestionJob.status == status)
    if source is not None:
        stmt = stmt.where(IngestionJob.source == source)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(IngestionJob.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).scalars().all()
    return list(rows), total