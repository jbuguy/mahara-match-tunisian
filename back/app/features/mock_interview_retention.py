"""Periodic deletion for expired private mock interview content."""

import asyncio
import logging
from datetime import datetime, timezone

from mahara_data.db.models.candidates import MockInterviewSession

from ..database import SessionLocal

logger = logging.getLogger(__name__)


def delete_expired_sessions() -> int:
    with SessionLocal() as db:
        deleted = db.query(MockInterviewSession).filter(
            MockInterviewSession.expires_at <= datetime.now(timezone.utc)
        ).delete(synchronize_session=False)
        db.commit()
        return deleted


async def run_retention_loop() -> None:
    while True:
        try:
            deleted = await asyncio.to_thread(delete_expired_sessions)
            if deleted:
                logger.info("Deleted %s expired mock interview sessions", deleted)
        except Exception:
            logger.exception("Mock interview retention cleanup failed")
        await asyncio.sleep(3600)
