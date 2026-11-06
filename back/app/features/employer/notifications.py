"""SMTP delivery worker for transactional employer notifications."""

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from ...config import get_settings
from ...database import SessionLocal
from ...email_delivery import mail_configured, send_email
from mahara_data.db.models.platform import NotificationOutbox

logger = logging.getLogger("notification_outbox")
MAX_ATTEMPTS = 5


def _claim_one() -> NotificationOutbox | None:
    now = datetime.now(timezone.utc)
    stale_sending = now - timedelta(minutes=10)
    with SessionLocal() as db:
        item = db.execute(
            select(NotificationOutbox).where(
                NotificationOutbox.attempts < MAX_ATTEMPTS,
                NotificationOutbox.next_attempt_at <= now,
                or_(NotificationOutbox.status.in_(("queued", "failed")),
                    (NotificationOutbox.status == "sending") & (NotificationOutbox.last_attempt_at < stale_sending)),
            ).order_by(NotificationOutbox.created_at.asc()).with_for_update(skip_locked=True).limit(1)
        ).scalar_one_or_none()
        if item is None:
            return None
        item.status = "sending"
        item.attempts += 1
        item.last_attempt_at = now
        item.last_error = None
        db.commit()
        db.refresh(item)
        return item


def _deliver(item: NotificationOutbox) -> None:
    settings = get_settings()
    if not mail_configured(settings):
        raise RuntimeError("Resend or SMTP email delivery must be configured")
    if not send_email(settings, item.recipient_email, item.subject, item.body, f"<{item.id}@mahara-match>"):
        raise RuntimeError("Transactional email delivery failed")


def process_one() -> bool:
    item = _claim_one()
    if item is None:
        return False
    with SessionLocal() as db:
        current = db.get(NotificationOutbox, item.id)
        if current is None:
            return True
        try:
            _deliver(current)
            current.status = "sent"
            current.sent_at = datetime.now(timezone.utc)
            current.last_error = None
        except Exception as error:
            current.status = "failed"
            delay = min(3600, 30 * (2 ** max(current.attempts - 1, 0)))
            current.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            current.last_error = str(error)[:1000]
            logger.exception("Notification delivery failed for outbox row %s", current.id)
        db.commit()
    return True


def run_forever() -> None:
    settings = get_settings()
    if not mail_configured(settings):
        raise RuntimeError("Configure RESEND_API_KEY and RESEND_FROM_EMAIL, or SMTP_HOST and SMTP_FROM_EMAIL")
    if settings.is_production and settings.smtp_host and not settings.smtp_use_starttls and not settings.resend_api_key:
        raise RuntimeError("SMTP_USE_STARTTLS must be enabled in production")
    logger.info("Starting transactional notification worker")
    while True:
        if not process_one():
            time.sleep(3)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
