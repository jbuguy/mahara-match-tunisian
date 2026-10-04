from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..metrics import METRICS
from ..services import monitoring as service

router = APIRouter(prefix="/admin/monitoring", tags=["admin-monitoring"])

MODULE_NAME = "wp5-admin-ministry"


class OverviewOut(BaseModel):
    module: str
    status: str
    uptime_seconds: float
    database_latency_ms: float | None
    requests_total: int
    refusals_total: int
    errors_total: int


class RouteStatsOut(BaseModel):
    route: str
    requests: int
    refusals: int
    errors: int
    avg_ms: float
    max_ms: float


class TaxonomyStatsOut(BaseModel):
    skills: dict[str, int]
    occupations: dict[str, int]
    suggestions: dict[str, int]
    occupations_without_skills: int


@router.get("/overview", response_model=OverviewOut, summary="Module health at a glance")
def overview(db: Annotated[Session, Depends(get_db)]) -> OverviewOut:
    latency = service.database_latency_ms(db)
    requests, refusals, errors = METRICS.totals()
    return OverviewOut(
        module=MODULE_NAME,
        status="ok" if latency is not None and errors == 0 else "degraded",
        uptime_seconds=METRICS.uptime_seconds(),
        database_latency_ms=latency,
        requests_total=requests,
        refusals_total=refusals,
        errors_total=errors,
    )


@router.get("/routes", response_model=list[RouteStatsOut], summary="Per-route traffic")
def route_stats() -> list[RouteStatsOut]:
    """Counters since the last restart. They live in memory, not in the database."""
    return [RouteStatsOut(**row) for row in METRICS.snapshot()]


@router.get("/taxonomy", response_model=TaxonomyStatsOut, summary="Referential quality")
def taxonomy_stats(db: Annotated[Session, Depends(get_db)]) -> TaxonomyStatsOut:
    """Governance indicators: what is waiting, and what is incomplete."""
    return TaxonomyStatsOut(**service.taxonomy_counts(db))