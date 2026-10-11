from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db

router = APIRouter(prefix="/health", tags=["health"])

MODULE_NAME = "wp5-admin-ministry"


class LivenessOut(BaseModel):
    status: str
    module: str


class DependencyOut(BaseModel):
    name: str
    status: str
    detail: str | None = None


class ReadinessOut(BaseModel):
    status: str
    module: str
    dependencies: list[DependencyOut]


@router.get("", response_model=LivenessOut, summary="Liveness probe")
def liveness() -> LivenessOut:
    """Answers as long as the process is up. No dependency is checked here."""
    return LivenessOut(status="ok", module=MODULE_NAME)


def _check(db: Session, name: str, statement: str) -> DependencyOut:
    try:
        db.execute(text(statement))
        return DependencyOut(name=name, status="up")
    except Exception as exc:
        db.rollback()
        # Only the exception class, never its message: it can carry credentials.
        return DependencyOut(name=name, status="down", detail=type(exc).__name__)


@router.get("/ready", response_model=ReadinessOut, summary="Readiness probe")
def readiness(response: Response, db: Session = Depends(get_db)) -> ReadinessOut:
    """Checks every dependency WP5 needs before it can serve traffic."""
    checks = [_check(db, "database", "select 1")]

    if checks[0].status == "up":
        checks.append(_check(db, "wp1_schema", "select 1 from skills limit 1"))
    else:
        checks.append(DependencyOut(name="wp1_schema", status="unknown"))

    ready = all(check.status == "up" for check in checks)
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessOut(
        status="ready" if ready else "degraded",
        module=MODULE_NAME,
        dependencies=checks,
    )