"""Employer-facing aggregate labour-market indicators."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from mahara_data.db.models.employers import Employer
from mahara_data.db.models.market import MarketDataset, MarketIndicator
from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Occupation
from mahara_data.enums import MarketDataOrigin, MarketIndicatorType

from ...database import get_db
from ...security import get_current_employer

MINIMUM_SALARY_SAMPLE_SIZE = 15


class SalaryBenchmarkOut(BaseModel):
    status: Literal["available", "suppressed", "unavailable"]
    occupation_code: str
    governorate_code: str | None
    region: str | None
    currency: Literal["TND"] = "TND"
    period_start: date | None = None
    period_end: date | None = None
    publisher: str | None = None
    sample_size: int | None = None
    minimum_sample_size: int = MINIMUM_SALARY_SAMPLE_SIZE
    median_tnd: float | None = None
    p25_tnd: float | None = None
    p75_tnd: float | None = None
    suppression_reason: str | None = None


router = APIRouter(prefix="/api/v1/employer/market", tags=["employer-market"])


@router.get("/salaries", response_model=SalaryBenchmarkOut)
def salary_benchmark(
    occupation_code: Annotated[str, Query(min_length=2, max_length=32)],
    db: Annotated[Session, Depends(get_db)],
    _employer: Annotated[Employer, Depends(get_current_employer)],
    governorate_code: Annotated[str | None, Query(max_length=8)] = None,
    region: Literal["grand_tunis"] | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> SalaryBenchmarkOut:
    """Read an official benchmark only when its source reports a safe sample size.

    Dataset rows are already aggregates. This endpoint never derives sample size
    from the number of rows, since one row may summarize an unknown population.
    """
    if governorate_code and region:
        raise HTTPException(status_code=422, detail="Choose a governorate or a broader region, not both")
    end = period_end or date.today()
    start = period_start or end - timedelta(days=365)
    if start > end:
        raise HTTPException(status_code=422, detail="period_start must be on or before period_end")
    occupation = db.execute(select(Occupation).where(Occupation.code == occupation_code)).scalar_one_or_none()
    if occupation is None:
        raise HTTPException(status_code=404, detail="Unknown occupation code")
    if governorate_code and db.get(Governorate, governorate_code) is None:
        raise HTTPException(status_code=404, detail="Unknown governorate code")

    statement = (
        select(MarketIndicator, MarketDataset)
        .join(MarketDataset, MarketDataset.id == MarketIndicator.dataset_id)
        .where(
            MarketIndicator.indicator_type == MarketIndicatorType.MEDIAN_SALARY,
            MarketIndicator.occupation_id == occupation.id,
            MarketIndicator.period_start >= start,
            MarketIndicator.period_end <= end,
            MarketDataset.origin == MarketDataOrigin.OFFICIAL,
        )
    )
    if governorate_code:
        statement = statement.where(MarketIndicator.governorate_code == governorate_code)
    elif region == "grand_tunis":
        # Aggregated medians cannot be recombined into a valid regional median.
        # Require an explicitly deposited region-level aggregate instead.
        statement = statement.where(
            MarketIndicator.governorate_code.is_(None),
            MarketIndicator.extra["region"].as_string() == "grand_tunis",
        )
    else:
        statement = statement.where(
            MarketIndicator.governorate_code.is_(None),
            MarketIndicator.extra["region"].as_string() == "national",
        )

    rows = db.execute(
        statement.order_by(MarketDataset.period_end.desc(), MarketDataset.created_at.desc())
    ).all()
    if not rows:
        return SalaryBenchmarkOut(
            status="unavailable",
            occupation_code=occupation_code,
            governorate_code=governorate_code,
            region=region,
            period_start=start,
            period_end=end,
            suppression_reason="No official salary dataset is available for this occupation and area.",
        )

    indicator, dataset = rows[0]
    sample = indicator.extra.get("sample_size") if isinstance(indicator.extra, dict) else None
    try:
        sample_size = int(sample) if sample is not None else None
    except (TypeError, ValueError):
        sample_size = None
    base = {
        "occupation_code": occupation_code,
        "governorate_code": governorate_code,
        "region": "Grand Tunis" if region == "grand_tunis" else None,
        "period_start": indicator.period_start,
        "period_end": indicator.period_end,
        "publisher": dataset.publisher,
    }
    if sample_size is None or sample_size < MINIMUM_SALARY_SAMPLE_SIZE:
        return SalaryBenchmarkOut(
            status="suppressed",
            **base,
            suppression_reason=(
                "The source does not provide a verifiable sample size."
                if sample_size is None
                else "The sample is below the minimum threshold."
            ),
        )

    extra = indicator.extra if isinstance(indicator.extra, dict) else {}
    return SalaryBenchmarkOut(
        status="available",
        **base,
        sample_size=sample_size,
        median_tnd=float(Decimal(indicator.value)),
        p25_tnd=_optional_decimal(extra.get("p25_tnd")),
        p75_tnd=_optional_decimal(extra.get("p75_tnd")),
    )


def _optional_decimal(value: object) -> float | None:
    try:
        return float(Decimal(str(value))) if value is not None else None
    except Exception:
        return None
