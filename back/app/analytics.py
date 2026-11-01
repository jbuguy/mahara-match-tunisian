"""Shared, privacy-safe product analytics helpers."""

from collections.abc import Mapping
from typing import Any
import uuid

from sqlalchemy.orm import Session

from mahara_data.db.models.platform import AnalyticsEvent


MAX_PROPERTIES = 32


def record_event(
    db: Session,
    event_name: str,
    *,
    actor_user_id: uuid.UUID | None = None,
    actor_role: str | None = None,
    entity_type: str | None = None,
    entity_id: str | uuid.UUID | None = None,
    session_id: str | None = None,
    properties: Mapping[str, Any] | None = None,
) -> AnalyticsEvent:
    """Queue one event; the caller's transaction controls persistence.

    Event properties must contain only aggregate or categorical values. Raw PII,
    CV text, transcripts, prompts, and tokens must never be passed here.
    """
    normalized_name = event_name.strip()
    if not normalized_name or len(normalized_name) > 80:
        raise ValueError("event_name must contain between 1 and 80 characters")
    safe_properties = dict(properties or {})
    if len(safe_properties) > MAX_PROPERTIES:
        raise ValueError(f"properties may contain at most {MAX_PROPERTIES} keys")

    event = AnalyticsEvent(
        event_name=normalized_name,
        actor_user_id=actor_user_id,
        actor_role=actor_role.strip().lower() if actor_role else None,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        session_id=session_id,
        properties=safe_properties,
    )
    db.add(event)
    return event
