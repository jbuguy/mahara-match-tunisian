import logging
from collections.abc import Iterator
from datetime import datetime
from typing import BinaryIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from ..auth import CurrentUser, get_current_user
from ..data_lifecycle import (
    EXPORT_CHUNK_BYTES,
    build_candidate_export,
    request_candidate_deletion,
)
from ..db import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/me", tags=["me"])


def _archive_chunks(archive: BinaryIO) -> Iterator[bytes]:
    try:
        while chunk := archive.read(EXPORT_CHUNK_BYTES):
            yield chunk
    finally:
        archive.close()


@router.get("/export")
def export_my_data(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    try:
        archive = build_candidate_export(db, current.user)
    except RuntimeError as exc:
        logger.exception("Could not build candidate data export for %s", current.user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="candidate export is temporarily unavailable",
        ) from exc
    archive.seek(0, 2)
    archive_size = archive.tell()
    archive.seek(0)
    return StreamingResponse(
        _archive_chunks(archive),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="mahara-match-data-export.zip"',
            "Cache-Control": "private, no-store",
            "Content-Length": str(archive_size),
        },
        background=BackgroundTask(archive.close),
    )


@router.delete("", status_code=status.HTTP_202_ACCEPTED)
def delete_my_account(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        purge_after: datetime = request_candidate_deletion(db, current.user)
    except RuntimeError as exc:
        logger.exception("Could not begin candidate deletion for %s", current.user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="candidate deletion is temporarily unavailable",
        ) from exc
    return {
        "status": "deletion_scheduled",
        "purge_after": purge_after.isoformat(),
    }
