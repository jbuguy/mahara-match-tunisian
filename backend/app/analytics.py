from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import HTTPException, Query, status


AgeGroup = Literal["15-24", "25-34", "35+"]


class AnalyticsFilters:
    def __init__(
        self,
        start_date: date | None = Query(default=None),
        end_date: date | None = Query(default=None),
        governorate_code: str | None = Query(default=None),
        sector_code: str | None = Query(default=None),
        age_group: AgeGroup | None = Query(default=None),
    ) -> None:
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="start_date must be on or before end_date.",
            )
        self.start_date = start_date
        self.end_date = end_date
        self.governorate_code = governorate_code
        self.sector_code = sector_code
        self.age_group = age_group


def previous_period(start_date: date | None, end_date: date | None) -> dict[str, date | None]:
    if start_date is None and end_date is None:
        return {"start_date": None, "end_date": None}
    effective_end = end_date or date.today()
    effective_start = start_date or effective_end
    if effective_start > effective_end:
        return {"start_date": None, "end_date": None}
    length = (effective_end - effective_start).days + 1
    previous_end = effective_start - timedelta(days=1)
    return {
        "start_date": previous_end - timedelta(days=length - 1),
        "end_date": previous_end,
    }


def suppress_small(count: int, k: int = 5) -> dict[str, int | bool | None]:
    if 0 < count < k:
        return {"value": None, "suppressed": True}
    return {"value": count, "suppressed": False}


def age_group_from_birth_year(birth_year: int | None, reference_date: date | None = None) -> str | None:
    if birth_year is None:
        return None
    reference_date = reference_date or date.today()
    age = reference_date.year - birth_year
    if 15 <= age <= 24:
        return "15-24"
    if 25 <= age <= 34:
        return "25-34"
    if age >= 35:
        return "35+"
    return None


def analytics_meta(definition: str, period: dict[str, date | None], source_url: str = "/admin/observatory") -> dict[str, object]:
    return {
        "source": "Mahara Match platform",
        "source_url": source_url,
        "period": period,
        "methodology": "Comptes agrégés et pseudo-anonymisés; les groupes de moins de cinq personnes sont supprimés.",
        "retrieved_at": datetime.now(timezone.utc),
        "definition": definition,
    }


def median(values: list[int | float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def sparkline(values: list[int | float], points: int = 12) -> list[int | float]:
    if len(values) >= points:
        return values[-points:]
    return [0] * (points - len(values)) + list(values)


def time_to_hire_bin(days: int) -> str:
    if days <= 7:
        return "0-7"
    if days <= 14:
        return "8-14"
    if days <= 21:
        return "15-21"
    if days <= 30:
        return "22-30"
    if days <= 45:
        return "31-45"
    if days <= 60:
        return "46-60"
    return "60+"


def candidates_per_open_position(candidates: int, open_positions: int) -> dict[str, object]:
    if open_positions == 0:
        return {"value": None, "reason": "no_open_positions"}
    if 0 < candidates < 5 or 0 < open_positions < 5:
        return {"value": None, "suppressed": True}
    return {"value": round(candidates / open_positions, 2), "suppressed": False}


def percentage_share(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(100 * numerator / denominator, 1)
