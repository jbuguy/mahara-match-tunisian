"""Database-backed worker for the configured official market-data JSON feed.

Run as a separate process: ``python -m app.features.ministry.worker``.
The feed must return a MarketDatasetSubmission JSON object (dataset + records).
"""

import logging
import time
from datetime import datetime, timezone
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


def _claim_one() -> IngestionJob | None:
    """Claim one queued refresh atomically; multiple worker processes are safe."""
    with SessionLocal() as db:
        job = db.execute(
            select(IngestionJob)
            .where(
                IngestionJob.source == IngestionSource.MINISTRY_MARKET,
                IngestionJob.status == ProcessingStatus.PENDING,
                IngestionJob.request_data["kind"].as_string() == "official_market_refresh",
            )
            .order_by(IngestionJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        ).scalar_one_or_none()
        if job is None:
            return None
        job.status = ProcessingStatus.PROCESSING
        job.pipeline_version = market.PIPELINE_VERSION
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        return job


def _feed_url(url: str) -> str:
    parsed = urlparse(url)
    settings = get_settings()
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("Configured feed URL must be an absolute HTTP(S) URL")
    if settings.environment.lower() == "production" and parsed.scheme != "https":
        raise ValueError("Configured feed URL must use HTTPS in production")
    return url


def _fetch(submission_data: dict) -> MarketDatasetSubmission:
    settings = get_settings()
    url = _feed_url(settings.ministry_market_feed_url or "")
    headers = {"Accept": "application/json"}
    if settings.ministry_market_feed_token:
        headers["Authorization"] = f"Bearer {settings.ministry_market_feed_token}"
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
        except Exception as exc:  # keep provider/parser details in job report, not HTTP response
            db.rollback()
            failed = db.get(IngestionJob, job.id)
            if failed is not None:
                failed.status = ProcessingStatus.FAILED
                failed.finished_at = datetime.now(timezone.utc)
                failed.records_total = 0
                failed.records_ok = 0
                failed.records_failed = 0
                failed.errors = [{"stage": "fetch_or_validate", "reason": str(exc)[:1000]}]
                db.commit()
            logger.exception("Official market refresh job %s failed", job.id)
    return True


def cleanup_expired_previews() -> int:
    """Delete abandoned private uploads after preview expiry; confirmed files remain retained."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        previews = db.execute(
            select(MarketUploadPreview).where(
                MarketUploadPreview.dataset_id.is_(None), MarketUploadPreview.expires_at <= now
            ).order_by(MarketUploadPreview.expires_at.asc()).with_for_update(skip_locked=True).limit(100)
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
