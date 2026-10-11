import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from mahara_data.db.models.candidates import Candidate, CandidateSkill
from mahara_data.db.models.employers import JobOffer, JobOfferSkill
from mahara_data.db.models.reference import Governorate
from mahara_data.enums import (
    ContractType,
    LiteracyLevel,
    OfferStatus,
    OnboardingPath,
    RequirementLevel,
    SkillSource,
)

from app.db import SessionLocal, engine
from app.main import app

client = TestClient(app)
ANALYTICS = "/api/v1/admin/analytics"
TAXONOMY = "/api/v1/admin/taxonomy"


def _database_is_up() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _database_is_up(), reason="database not reachable")


def _a_governorate() -> str | None:
    with SessionLocal() as db:
        return db.execute(select(Governorate.code).limit(1)).scalar_one_or_none()


GOVERNORATE = _a_governorate() if _database_is_up() else None
needs_governorates = pytest.mark.skipif(
    GOVERNORATE is None, reason="governorates table not seeded"
)


def _create_skill(label: str) -> tuple[str, uuid.UUID]:
    code = f"SK-8{uuid.uuid4().hex[:6]}"
    created = client.post(
        f"{TAXONOMY}/skills", json={"code": code, "label_fr": label, "skill_type": "hard"}
    )
    assert created.status_code == 201
    return code, uuid.UUID(created.json()["skill_id"])


def _seed_offers(skill_id: uuid.UUID, count: int, *, days_ago: int = 30) -> None:
    """Plays WP4's part: published offers requiring the skill."""
    published = datetime.now(timezone.utc) - timedelta(days=days_ago)
    with SessionLocal() as db:
        for index in range(count):
            offer = JobOffer(
                title=f"Poste de test {index}",
                description_raw="Offre creee par les tests WP5.",
                contract_type=ContractType.CDD,
                governorate_code=GOVERNORATE,
                status=OfferStatus.PUBLISHED,
                published_at=published,
            )
            db.add(offer)
            db.flush()
            db.add(
                JobOfferSkill(
                    job_offer_id=offer.id,
                    skill_id=skill_id,
                    requirement=RequirementLevel.REQUIRED,
                )
            )
        db.commit()


def _seed_candidates(skill_id: uuid.UUID, count: int) -> None:
    """Plays WP2's part: candidates holding the skill."""
    with SessionLocal() as db:
        for _ in range(count):
            candidate = Candidate(
                onboarding_path=OnboardingPath.CV_UPLOAD,
                literacy_level=LiteracyLevel.LITERATE,
                governorate_code=GOVERNORATE,
            )
            db.add(candidate)
            db.flush()
            db.add(
                CandidateSkill(
                    candidate_id=candidate.id,
                    skill_id=skill_id,
                    level=3,
                    source=SkillSource.CV,
                )
            )
        db.commit()


def _map(**params) -> dict:
    query = {"governorate_code": GOVERNORATE, "limit": 500, **params}
    response = client.get(f"{ANALYTICS}/skill-gaps", params=query)
    assert response.status_code == 200
    return response.json()


def _cell_for(code: str, **params) -> dict | None:
    return next((cell for cell in _map(**params)["cells"] if cell["skill_code"] == code), None)


@needs_db
@needs_governorates
def test_a_skill_nobody_has_is_published_as_a_total_gap():
    code, skill_id = _create_skill("Soudure TIG")
    _seed_offers(skill_id, 3)

    cell = _cell_for(code)
    # Zero people behind the cell means nobody to protect: it is published.
    assert cell is not None
    assert (cell["demand_count"], cell["supply_count"]) == (3, 0)
    assert cell["gap_ratio"] == 3.0


@needs_db
@needs_governorates
def test_a_cell_describing_fewer_than_ten_people_is_withheld():
    code, skill_id = _create_skill("Calligraphie")
    _seed_offers(skill_id, 2)
    _seed_candidates(skill_id, 3)

    assert _cell_for(code) is None

    body = _map()
    assert body["k_anonymity"] == 10
    assert body["cells_suppressed"] >= 1  # the count is public, the cell is not


@needs_db
@needs_governorates
def test_ten_people_is_enough_to_publish():
    code, skill_id = _create_skill("Maconnerie")
    _seed_offers(skill_id, 5)
    _seed_candidates(skill_id, 10)

    cell = _cell_for(code)
    assert cell is not None
    assert cell["supply_count"] == 10
    assert cell["gap_ratio"] == 0.5


@needs_db
@needs_governorates
def test_demand_outside_the_window_is_not_counted():
    code, skill_id = _create_skill("Vannerie")
    _seed_offers(skill_id, 4, days_ago=800)

    # Default window is the last 365 days.
    assert _cell_for(code) is None
    # Widen it and the same offers reappear: the window was the cause, not the data.
    assert _cell_for(code, period_start="2020-01-01") is not None