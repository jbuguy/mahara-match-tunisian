import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from mahara_data.db.models.platform import Document, IngestionJob, MarketUploadPreview
from mahara_data.enums import DocumentType, IngestionSource, MarketDataOrigin, ProcessingStatus
from mahara_data.schemas.common import Page
from mahara_data.schemas.market import MarketDatasetCreate

from ....database import get_db
from ....models import User
from ....security import require_roles
from ..schemas import (
    IngestionJobOut, IngestionReport, MarketDatasetOut, MarketDatasetSubmission,
    MarketRefreshRequest, MarketUploadConfirm, MarketUploadPreviewOut, RecordRejection,
)
from ..services import audit, ingestion as ingestion_service, market as service
from ..services.market_uploads import MAX_UPLOAD_BYTES, parse_market_file
from ....config import get_settings

router = APIRouter(
    prefix="/admin/market",
    tags=["admin-market"],
    dependencies=[Depends(require_roles("ministry_admin"))],
)


@router.post("/datasets/upload/preview", response_model=MarketUploadPreviewOut, status_code=201)
async def preview_dataset_upload(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles("ministry_admin"))],
    dataset_json: Annotated[str, Form(alias="dataset")],
    file: Annotated[UploadFile, File()],
) -> MarketUploadPreviewOut:
    from datetime import datetime, timedelta, timezone
    import hashlib
    import mimetypes
    from pathlib import PurePath
    import uuid
    from pydantic import ValidationError

    try:
        dataset = MarketDatasetCreate.model_validate_json(dataset_json)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors(include_input=False)) from error
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Files are limited to {MAX_UPLOAD_BYTES} bytes")
    accepted, rejected = parse_market_file(file.filename or "upload", content)
    if not accepted:
        raise HTTPException(status_code=422, detail={"message": "No valid records to import", "rejections": rejected[:50]})
    settings = get_settings()
    preview_id = uuid.uuid4()
    safe_filename = PurePath(file.filename or "dataset").name
    key = f"market-previews/{admin.id}/{preview_id}/{safe_filename}"
    try:
        from .... import storage
        storage_path = storage.put_private(key, content, mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream")
    except Exception as error:
        raise HTTPException(status_code=503, detail="Private dataset storage is unavailable or not configured") from error
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
    preview = MarketUploadPreview(
        id=preview_id, actor_user_id=admin.id, storage_path=storage_path,
        original_filename=safe_filename[:255],
        mime_type=mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream",
        size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest(),
        dataset_data=dataset.model_dump(mode="json"),
        preview_data={"records_total": len(accepted) + len(rejected), "records_valid": len(accepted),
                      "rejections": rejected}, expires_at=expires_at,
    )
    try:
        db.add(preview)
        db.commit()
    except Exception as error:
        db.rollback()
        try:
            storage.delete_private(key)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Could not record the upload preview") from error
    sample = accepted[:20]
    return MarketUploadPreviewOut(
        preview_id=preview.id, expires_at=expires_at, size_bytes=len(content),
        sha256=preview.sha256, records_total=len(accepted) + len(rejected),
        records_valid=len(accepted), records_invalid=len(rejected), sample=sample,
        rejections=[RecordRejection(**item) for item in rejected[:50]],
    )


@router.post("/datasets/upload/{preview_id}/confirm", response_model=IngestionReport, status_code=201)
def confirm_dataset_upload(
    preview_id: uuid.UUID,
    payload: MarketUploadConfirm,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles("ministry_admin"))],
) -> IngestionReport:
    from datetime import datetime, timezone
    import hashlib
    from .... import storage

    preview = db.query(MarketUploadPreview).filter(
        MarketUploadPreview.id == preview_id, MarketUploadPreview.actor_user_id == admin.id
    ).with_for_update().first()
    if preview is None:
        raise HTTPException(status_code=404, detail="Upload preview not found")
    if preview.dataset_id is not None:
        dataset = service.get_dataset(db, preview.dataset_id)
        job = ingestion_service.get_job(db, dataset.ingestion_job_id) if dataset else None
        if dataset and job:
            return IngestionReport(dataset_id=dataset.id, job_id=job.id, status=job.status,
                records_total=job.records_total, records_ok=job.records_ok, records_failed=job.records_failed,
                rejections=[RecordRejection(**row) for row in job.errors if "index" in row and "reason" in row])
        raise HTTPException(status_code=409, detail="Upload preview was already confirmed")
    now = datetime.now(timezone.utc)
    expiry = preview.expires_at if preview.expires_at.tzinfo else preview.expires_at.replace(tzinfo=timezone.utc)
    if expiry <= now:
        raise HTTPException(status_code=410, detail="Upload preview expired; upload the file again")
    try:
        content = storage.get_private(preview.storage_path.split("/", 1)[1])
        accepted, rejected = parse_market_file(preview.original_filename, content)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Could not retrieve or validate the uploaded file") from error
    if rejected and not payload.accept_valid_rows:
        raise HTTPException(status_code=409, detail={
            "message": "Confirm partial import explicitly to accept valid rows and skip rejected rows",
            "records_valid": len(accepted), "records_invalid": len(rejected), "rejections": rejected[:50],
        })
    if not accepted:
        raise HTTPException(status_code=422, detail="No valid records to import")
    if preview.sha256 != hashlib.sha256(content).hexdigest():
        raise HTTPException(status_code=409, detail="Stored file hash differs from the reviewed preview")

    dataset_data = dict(preview.dataset_data)
    document = Document(
        doc_type=DocumentType.MARKET_DATASET, owner_user_id=admin.id,
        storage_path=preview.storage_path, mime_type=preview.mime_type,
        size_bytes=preview.size_bytes, sha256=preview.sha256,
    )
    db.add(document)
    db.flush()
    dataset_data["document_id"] = str(document.id)
    submission = MarketDatasetSubmission.model_validate({"dataset": dataset_data, "records": accepted})
    dataset, job, mapping_rejections = service.ingest(db, submission, admin.id, commit=False)
    parse_errors = [{**item, "stage": "file_validation"} for item in rejected]
    job.records_total = int(preview.preview_data["records_total"])
    job.records_failed += len(rejected)
    job.records_ok = len(accepted) - len(mapping_rejections)
    job.errors = [*mapping_rejections, *parse_errors]
    if job.records_ok == 0:
        job.status = ProcessingStatus.FAILED
    audit.record(db, "market.dataset_file_confirmed", "market_dataset", str(dataset.id),
        {"sha256": preview.sha256, "records_ok": job.records_ok, "records_failed": job.records_failed},
        actor_user_id=admin.id)
    preview.dataset_id = dataset.id
    preview.confirmed_at = now
    db.commit()
    db.refresh(dataset)
    db.refresh(job)
    return IngestionReport(dataset_id=dataset.id, job_id=job.id, status=job.status,
        records_total=job.records_total, records_ok=job.records_ok, records_failed=job.records_failed,
        rejections=[RecordRejection(**row) for row in job.errors if "index" in row and "reason" in row])


@router.post("/datasets", response_model=IngestionReport, status_code=status.HTTP_201_CREATED)
def deposit_dataset(
    submission: MarketDatasetSubmission,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles("ministry_admin"))],
) -> IngestionReport:
    """Ministry deposit. Valid rows are kept; rejected rows come back with their position."""
    dataset, job, rejections = service.ingest(db, submission, admin.id)
    return IngestionReport(
        dataset_id=dataset.id,
        job_id=job.id,
        status=job.status,
        records_total=job.records_total,
        records_ok=job.records_ok,
        records_failed=job.records_failed,
        rejections=[RecordRejection(**item) for item in rejections],
    )


@router.post("/refresh", response_model=IngestionJobOut, status_code=status.HTTP_202_ACCEPTED)
def enqueue_refresh(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles("ministry_admin"))],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
    request: MarketRefreshRequest | None = None,
) -> IngestionJobOut:
    """Queue a durable pull from the deployment-configured official JSON feed."""
    settings = get_settings()
    if not settings.ministry_market_feed_url:
        raise HTTPException(status_code=503, detail="Official market feed is not configured")

    key = f"market-refresh:{idempotency_key}"
    previous = db.execute(
        select(IngestionJob).where(IngestionJob.idempotency_key == key)
    ).scalar_one_or_none()
    if previous is not None:
        return ingestion_service.to_read(previous)

    # Serialize enqueue checks across API workers; the durable job itself is claimed by SKIP LOCKED.
    db.execute(text("select pg_advisory_xact_lock(519842771)"))
    previous = db.execute(
        select(IngestionJob).where(IngestionJob.idempotency_key == key)
    ).scalar_one_or_none()
    if previous is not None:
        db.rollback()
        return ingestion_service.to_read(previous)
    active = db.execute(
        select(IngestionJob).where(
            IngestionJob.source == IngestionSource.MINISTRY_MARKET,
            IngestionJob.status.in_((ProcessingStatus.PENDING, ProcessingStatus.PROCESSING)),
            IngestionJob.request_data["kind"].as_string() == "official_market_refresh",
        ).limit(1)
    ).scalar_one_or_none()
    if active is not None:
        db.rollback()
        raise HTTPException(status_code=409, detail="An official market refresh is already queued or running")

    job = IngestionJob(
        source=IngestionSource.MINISTRY_MARKET,
        status=ProcessingStatus.PENDING,
        pipeline_version=service.PIPELINE_VERSION,
        request_data={
            "kind": "official_market_refresh",
            "since": request.since.isoformat() if request and request.since else None,
        },
        idempotency_key=key,
        triggered_by=admin.id,
    )
    db.add(job)
    db.flush()
    audit.record(
        db, "market.refresh_queued", "ingestion_job", str(job.id),
        {"since": job.request_data["since"]}, actor_user_id=admin.id,
    )
    db.commit()
    db.refresh(job)
    return ingestion_service.to_read(job)


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
