"""Applications (WP6 -> WP4) and hiring feedback (WP4 -> WP1/WP3/WP5)."""

import uuid
from datetime import datetime

from pydantic import Field

from ..enums import ApplicationStatus, HiringDecision
from .common import Contract


class ApplicationCreate(Contract):
    """1-click application: the structured profile is attached server-side, not re-sent."""

    candidate_id: uuid.UUID
    job_offer_id: uuid.UUID
    cover_note: str | None = Field(default=None, max_length=2000)


class ApplicationRead(Contract):
    application_id: uuid.UUID
    candidate_id: uuid.UUID
    job_offer_id: uuid.UUID
    match_id: uuid.UUID | None = None
    score_global: float | None = Field(default=None, ge=0, le=100)
    status: ApplicationStatus
    applied_at: datetime
    updated_at: datetime


class ApplicationStatusUpdate(Contract):
    status: ApplicationStatus


class HiringFeedback(Contract):
    application_id: uuid.UUID
    employer_id: uuid.UUID
    decision: HiringDecision
    reason_code: str | None = Field(
        default=None, max_length=64, examples=["skills_mismatch", "experience_too_low", "position_filled"]
    )
    match_quality: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
