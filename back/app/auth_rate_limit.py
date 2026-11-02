"""Database-backed per-IP rate limits for unauthenticated account endpoints."""

from __future__ import annotations

import hashlib
import hmac
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import AuthRateLimitBucket

_cleanup_lock = threading.Lock()
_last_cleanup_at = 0.0
_CLEANUP_INTERVAL_SECONDS = 3600
_BUCKET_RETENTION = timedelta(days=1)


def rate_limit_dependency(
    action: str,
    limit_setting: str,
    window_setting: str,
) -> Callable[..., None]:
    def enforce_rate_limit(
        request: Request,
        db: Session = Depends(get_db),
    ) -> None:
        global _last_cleanup_at

        settings = get_settings()
        limit = getattr(settings, limit_setting)
        window_seconds = getattr(settings, window_setting)
        now = datetime.now(timezone.utc)
        window_epoch = int(now.timestamp()) // window_seconds * window_seconds
        window_start = datetime.fromtimestamp(window_epoch, timezone.utc)
        client_ip = request.client.host if request.client else "unknown"
        bucket_key = hmac.new(
            settings.jwt_secret.encode("utf-8"),
            f"{action}:{client_ip}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            insert = postgresql_insert
        elif dialect == "sqlite":
            insert = sqlite_insert
        else:
            raise RuntimeError(f"Auth rate limiting does not support database dialect {dialect}")

        statement = insert(AuthRateLimitBucket).values(
            bucket_key=bucket_key,
            window_start=window_start,
            request_count=1,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["bucket_key", "window_start"],
            set_={"request_count": AuthRateLimitBucket.request_count + 1},
        ).returning(AuthRateLimitBucket.request_count)
        request_count = db.execute(statement).scalar_one()

        monotonic_now = time.monotonic()
        with _cleanup_lock:
            if monotonic_now - _last_cleanup_at >= _CLEANUP_INTERVAL_SECONDS:
                db.execute(
                    delete(AuthRateLimitBucket).where(
                        AuthRateLimitBucket.window_start < now - _BUCKET_RETENTION
                    )
                )
                _last_cleanup_at = monotonic_now

        db.commit()
        if request_count > limit:
            retry_after = max(
                1,
                int((window_start + timedelta(seconds=window_seconds) - now).total_seconds()),
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )

    return enforce_rate_limit
