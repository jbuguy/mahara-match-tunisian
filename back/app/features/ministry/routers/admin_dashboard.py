from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ....analytics import record_event
from ....database import get_db
from ....models import User
from ....security import require_any_role
from ..metrics import METRICS
from mahara_data.db.models.employers import Application, JobOffer
from mahara_data.db.models.platform import AnalyticsEvent


router = APIRouter(
    prefix="/admin/analytics",
    tags=["admin-analytics"],
    dependencies=[Depends(require_any_role("admin", "ministry_admin"))],
)


def _count(db: Session, model, *, since: datetime | None = None) -> int:
    statement = select(func.count()).select_from(model)
    if since is not None and hasattr(model, "created_at"):
        statement = statement.where(model.created_at >= since)
    return int(db.execute(statement).scalar_one())


@router.get("/overview", response_model=dict)
def admin_overview(
    db: Session = Depends(get_db),
    current: User = Depends(require_any_role("admin", "ministry_admin")),
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> dict:
    """Operational snapshot for platform admins and ministry operators."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    event_rows = db.execute(
        select(AnalyticsEvent.event_name, func.count())
        .where(AnalyticsEvent.created_at >= since)
        .group_by(AnalyticsEvent.event_name)
        .order_by(func.count().desc(), AnalyticsEvent.event_name)
    ).all()
    requests, refusals, errors = METRICS.totals()
    record_event(
        db,
        "admin.analytics_viewed",
        actor_user_id=current.id,
        actor_role="admin",
        properties={"period_days": days},
    )
    db.commit()
    return {
        "period": {"start": since.isoformat(), "end": now.isoformat(), "days": days},
        "users": {"total": _count(db, User), "new": _count(db, User, since=since)},
        "offers": {"total": _count(db, JobOffer), "new": _count(db, JobOffer, since=since)},
        "applications": {"total": _count(db, Application), "new": _count(db, Application, since=since)},
        "product_events": {
            "total": sum(int(row[1]) for row in event_rows),
            "by_name": {row[0]: int(row[1]) for row in event_rows},
        },
        "service": {"requests_total": requests, "refusals_total": refusals, "errors_total": errors},
    }
