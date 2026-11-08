import re
from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NationalIndicator


INDICATOR_IDS = {
    "worldbank-tn-unemployment": "total_unemployment",
    "worldbank-tn-youth-unemployment": "youth_unemployment_15_24",
    "worldbank-tn-employment-to-population": "employment_to_population",
    "tunisia-agridata-jobs-created": "agridata_jobs_created",
}

SERIES_UNITS = {
    "total_unemployment": "%",
    "youth_unemployment_15_24": "%",
    "employment_to_population": "%",
    "agridata_jobs_created": "jobs",
}


def parse_annual_observations(content: str) -> list[tuple[int, float]]:
    match = re.search(r"Annual observations:\s*(.+)\.", content, flags=re.IGNORECASE | re.DOTALL)
    if match:
        text = match.group(1)
    else:
        text = content
    observations: list[tuple[int, float]] = []
    for year_text, value_text in re.findall(r"\b(20\d{2})\s*:\s*([-+]?(?:\d+(?:[.,]\d+)?))", text):
        observations.append((int(year_text), float(value_text.replace(",", "."))))
    return observations


def refresh_national_indicators(session: Session, documents: Iterable[object]) -> int:
    count = 0
    session.query(NationalIndicator).delete()
    for document in documents:
        external_id = getattr(document, "external_id", "")
        indicator_id = INDICATOR_IDS.get(external_id)
        if not indicator_id:
            continue
        for year, value in parse_annual_observations(document.content):
            session.add(NationalIndicator(
                indicator_id=indicator_id,
                year=year,
                value=value,
                unit=SERIES_UNITS[indicator_id],
                source_document_id=document.id,
            ))
            count += 1
    session.commit()
    return count


def national_series(session: Session, indicator_id: str) -> list[NationalIndicator]:
    return list(session.scalars(
        select(NationalIndicator)
        .where(NationalIndicator.indicator_id == indicator_id)
        .order_by(NationalIndicator.year)
    ).all())
