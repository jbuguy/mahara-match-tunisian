from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import SkillGapMap
from ..services import analytics as service

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


@router.get("/skill-gaps", response_model=SkillGapMap)
def skill_gaps(
    db: Annotated[Session, Depends(get_db)],
    period_start: date | None = None,
    period_end: date | None = None,
    governorate_code: Annotated[str | None, Query(max_length=8)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> SkillGapMap:
    """Skill-gap cartography served to the ministry. The k threshold always applies."""
    end = period_end or date.today()
    start = period_start or end - timedelta(days=365)

    cells, suppressed = service.skill_gap_map(
        db,
        period_start=start,
        period_end=end,
        governorate_code=governorate_code,
        limit=limit,
    )
    return SkillGapMap(
        period_start=start,
        period_end=end,
        k_anonymity=service.K_ANONYMITY,
        cells_suppressed=suppressed,
        cells=cells,
    )