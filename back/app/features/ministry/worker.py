import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

from mahara_data.db.models.platform import IngestionJob, MarketUploadPreview
from mahara_data.enums import IngestionSource, MarketDataOrigin, ProcessingStatus

from ...config import get_settings
from ...database import SessionLocal
from .schemas import MarketDatasetSubmission
from .services import market

logger = logging.getLogger("market_ingestion")
MAX_FEED_BYTES = 10 * 1024 * 1024
MAX_RETRY_ATTEMPTS = 3


def _build_feed_headers(settings) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    token = (getattr(settings, "ministry_market_feed_token", "") or "").strip()
    if token:
        auth = token if token.lower().startswith("bearer ") else f"Bearer {token}"
        headers["Authorization"] = auth
    return headers


def _job_ready(job: IngestionJob) -> bool:
    payload = job.request_data or {}
    now = datetime.now(timezone.utc)

    lease_expires_at = getattr(job, "lease_expires_at", None)
    if lease_expires_at is not None:
        if lease_expires_at.tzinfo is None:
            lease_expires_at = lease_expires_at.replace(tzinfo=timezone.utc)
        if lease_expires_at > now:
            return False

    retry_at = payload.get("next_retry_at")
    if not retry_at:
        return True
    if isinstance(retry_at, str):
        try:
            retry_at = datetime.fromisoformat(retry_at)
        except ValueError:
            return True
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return retry_at <= now


def _claim_one() -> IngestionJob | None:
    """Claim one queued refresh atomically; multiple worker processes are safe."""
    settings = get_settings()
    worker_id = f"market-worker-{uuid.uuid4().hex[:12]}"
    lease_seconds = max(float(getattr(settings, "ministry_market_worker_lease_seconds", 120.0)), 5.0)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        jobs = db.execute(
            select(IngestionJob)
            .where(
                IngestionJob.source == IngestionSource.MINISTRY_MARKET,
                IngestionJob.status == ProcessingStatus.PENDING,
                IngestionJob.request_data["kind"].as_string() == "official_market_refresh",
            )
            .order_by(IngestionJob.created_at.asc())
        ).scalars().all()
        job = next((row for row in jobs if _job_ready(row)), None)
        if job is None:
            return None

        payload = dict(job.request_data or {})
        attempts = int(payload.get("attempts", job.attempt_count or 0))
        job.status = ProcessingStatus.PROCESSING
        job.pipeline_version = market.PIPELINE_VERSION
        job.started_at = now
        job.finished_at = None
        job.worker_id = worker_id
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        job.attempt_count = attempts
        payload["next_retry_at"] = None
        job.request_data = payload
        db.commit()
        db.refresh(job)
        return job


def _feed_url(url: str) -> str:
    parsed = urlparse(url)
    settings = get_settings()
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("Configured feed URL must be an absolute HTTP(S) URL")
    if settings.is_production and parsed.scheme != "https":
        raise ValueError("Configured feed URL must use HTTPS in production")
    return url


def _fetch(submission_data: dict) -> MarketDatasetSubmission:
    settings = get_settings()
    url = _feed_url(settings.ministry_market_feed_url or "")
    headers = _build_feed_headers(settings)
    params = {"since": submission_data["since"]} if submission_data.get("since") else None
    timeout = httpx.Timeout(settings.ministry_market_feed_timeout_seconds)
    chunks: list[bytes] = []
    size = 0
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        with client.stream("GET", url, headers=headers, params=params) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_FEED_BYTES:
                    raise ValueError(f"Feed response exceeds the {MAX_FEED_BYTES}-byte limit")
                chunks.append(chunk)
    submission = MarketDatasetSubmission.model_validate_json(b"".join(chunks))
    if submission.dataset.origin is not MarketDataOrigin.OFFICIAL:
        raise ValueError("Configured official feed must identify its dataset origin as official")
    if len(submission.records) > 5000:
        raise ValueError("Feed response exceeds the 5000-record limit")
    return submission


def process_one() -> bool:
    job = _claim_one()
    if job is None:
        return False

    with SessionLocal() as db:
        current = db.get(IngestionJob, job.id)
        if current is None:
            return True
        try:
            submission = _fetch(current.request_data or {})
            market.ingest(db, submission, current.triggered_by, existing_job=current)
        except Exception as exc:
            db.rollback()
            failed = db.get(IngestionJob, job.id)
            if failed is not None:
                payload = dict(failed.request_data or {})
                attempts = int(payload.get("attempts", 0))
                retry_delay_seconds = min(30 * (2 ** attempts), 900)
                should_retry = attempts < MAX_RETRY_ATTEMPTS
                failed.errors = [{"stage": "fetch_or_validate", "reason": str(exc)[:1000]}]
                if should_retry:
                    payload["attempts"] = attempts + 1
                    payload["last_error"] = str(exc)[:1000]
                    payload["next_retry_at"] = (datetime.now(timezone.utc) + timedelta(seconds=retry_delay_seconds)).isoformat()
                    failed.status = ProcessingStatus.PENDING
                    failed.finished_at = None
                    failed.records_total = 0
                    failed.records_ok = 0
                    failed.records_failed = 0
                    failed.request_data = payload
                    db.commit()
                    logger.warning("Official market refresh job %s failed; retrying in %s seconds", failed.id, retry_delay_seconds)
                    return True
                failed.status = ProcessingStatus.FAILED
                failed.finished_at = datetime.now(timezone.utc)
                failed.records_total = 0
                failed.records_ok = 0
                failed.records_failed = 0
                failed.request_data = {**payload, "attempts": attempts, "last_error": str(exc)[:1000]}
                db.commit()
            logger.exception("Official market refresh job %s failed", job.id)
    return True


def cleanup_expired_previews() -> int:
    """Delete abandoned private uploads after preview expiry; confirmed files remain retained."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        previews = db.execute(
            select(MarketUploadPreview)
            .where(
                MarketUploadPreview.dataset_id.is_(None),
                MarketUploadPreview.expires_at <= now,
            )
            .order_by(MarketUploadPreview.expires_at.asc())
            .with_for_update(skip_locked=True)
            .limit(100)
        ).scalars().all()
        if not previews:
            return 0
        from ... import storage

        for preview in previews:
            try:
                storage.delete_private(preview.storage_path.split("/", 1)[1])
            except Exception:
                logger.exception("Could not remove expired market upload %s", preview.id)
                continue
            db.delete(preview)
        db.commit()
        return len(previews)


def run_forever() -> None:
    settings = get_settings()
    if settings.ministry_market_worker_poll_seconds <= 0:
        raise RuntimeError("MINISTRY_MARKET_WORKER_POLL_SECONDS must be positive")
    logger.info("Starting market ingestion worker; official feed %s", "enabled" if settings.ministry_market_feed_url else "disabled")
    last_cleanup = 0.0
    while True:
        if time.monotonic() - last_cleanup >= 600:
            try:
                cleanup_expired_previews()
            except Exception:
                logger.exception("Expired market-upload cleanup failed")
            last_cleanup = time.monotonic()
        if not process_one():
            time.sleep(settings.ministry_market_worker_poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
