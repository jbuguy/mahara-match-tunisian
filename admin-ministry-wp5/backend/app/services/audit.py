from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from mahara_data.db.models.platform import AuditLog

# WP1's model allows a service actor, so WP5 can audit before authentication exists.
SERVICE_NAME = "wp5-admin"


def record(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Stage an audit entry inside the caller's transaction. Never commits on its own:
    the act and its trace must land together, or neither of them does."""
    db.add(
        AuditLog(
            actor_service=SERVICE_NAME,
            # TODO: fill actor_user_id once authentication lands.
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
    )


def list_entries(
    db: Session,
    *,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[AuditLog], int]:
    """Most recent first: an audit trail is read backwards, from what just happened."""
    from sqlalchemy import func

    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(AuditLog.id.desc()).limit(page_size).offset((page - 1) * page_size)
    ).scalars().all()
    return list(rows), total