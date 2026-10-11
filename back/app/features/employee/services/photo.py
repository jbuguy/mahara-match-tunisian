"""The candidate's own photo, stored in candidate_pii.photo. Without one, the UI shows the Google photo."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..models import Candidate, CandidatePii

# The browser sends a 256x256 JPEG (about 20-40 KB); this leaves room without accepting big files.
MAX_PHOTO_BYTES = 300_000
JPEG_START = b"\xff\xd8\xff"


def _candidate_id(user_id: uuid.UUID):
    return select(Candidate.id).where(Candidate.user_id == user_id).scalar_subquery()


def get_photo(db: Session, user_id: uuid.UUID) -> bytes | None:
    return db.scalar(select(CandidatePii.photo).where(CandidatePii.candidate_id == _candidate_id(user_id)))


def set_photo(db: Session, user_id: uuid.UUID, photo: bytes | None) -> bool:
    """Store (or with None, remove) the photo. False when the candidate has no profile yet."""
    result = db.execute(
        update(CandidatePii).where(CandidatePii.candidate_id == _candidate_id(user_id)).values(photo=photo)
    )
    db.commit()
    return result.rowcount > 0
