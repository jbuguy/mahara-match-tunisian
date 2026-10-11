import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app

client = TestClient(app)
MARKET = "/api/v1/admin/market"
TAXONOMY = "/api/v1/admin/taxonomy"
MONITORING = "/api/v1/admin/monitoring"


def _database_is_up() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _database_is_up(), reason="database not reachable")


def _create_skill(label: str) -> str:
    code = f"SK-8{uuid.uuid4().hex[:6]}"
    created = client.post(
        f"{TAXONOMY}/skills", json={"code": code, "label_fr": label, "skill_type": "hard"}
    )
    assert created.status_code == 201
    return code


def _header(title: str = "Enquete emploi T1 2026") -> dict:
    return {
        "title": title,
        "origin": "official",
        "publisher": "Ministere de l'Emploi",
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
    }


def _skill_demand(skill_code: str, value: float) -> dict:
    return {
        "indicator_type": "skill_demand",
        "skill_code": skill_code,
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "value": value,
        "unit": "count",
    }


@needs_db
def test_a_valid_deposit_keeps_every_row():
    first = _create_skill("Soudure")
    second = _create_skill("Maconnerie")

    report = client.post(
        f"{MARKET}/datasets",
        json={
            "dataset": _header(),
            "records": [_skill_demand(first, 320), _skill_demand(second, 145)],
        },
    )
    assert report.status_code == 201

    body = report.json()
    assert body["status"] == "completed"
    assert (body["records_total"], body["records_ok"], body["records_failed"]) == (2, 2, 0)
    assert body["rejections"] == []

    stored = client.get(f"{MARKET}/datasets/{body['dataset_id']}").json()
    assert stored["indicator_count"] == 2
    assert stored["job_status"] == "completed"


@needs_db
def test_unknown_codes_reject_rows_never_the_dataset():
    known = _create_skill("Plomberie")
    orphan_row = {
        "indicator_type": "vacancies",
        "occupation_code": "OC-999999",
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "value": 12,
        "unit": "count",
    }

    body = client.post(
        f"{MARKET}/datasets",
        json={"dataset": _header(), "records": [_skill_demand(known, 50), orphan_row]},
    ).json()

    # The deposit stands: one row in, one row reported back.
    assert body["status"] == "completed"
    assert (body["records_ok"], body["records_failed"]) == (1, 1)
    assert body["rejections"][0]["index"] == 1  # its position in the submitted file
    assert "OC-999999" in body["rejections"][0]["reason"]

    stored = client.get(f"{MARKET}/datasets/{body['dataset_id']}").json()
    assert stored["indicator_count"] == 1


@needs_db
def test_a_deposit_where_nothing_resolves_is_marked_failed():
    body = client.post(
        f"{MARKET}/datasets",
        json={"dataset": _header(), "records": [_skill_demand("SK-999999", 10)]},
    ).json()

    assert body["status"] == "failed"
    assert (body["records_ok"], body["records_failed"]) == (0, 1)


@needs_db
def test_the_deposit_is_audited():
    skill = _create_skill("Electricite")
    body = client.post(
        f"{MARKET}/datasets",
        json={"dataset": _header(), "records": [_skill_demand(skill, 77)]},
    ).json()

    entries = client.get(
        f"{MONITORING}/audit", params={"entity_id": body["dataset_id"]}
    ).json()["items"]

    assert entries[0]["action"] == "market.dataset_ingested"
    assert entries[0]["payload"]["publisher"] == "Ministere de l'Emploi"
    assert entries[0]["payload"]["records_ok"] == 1


@needs_db
def test_an_inverted_period_is_refused_by_the_contract():
    header = _header()
    header["period_start"], header["period_end"] = header["period_end"], header["period_start"]

    refused = client.post(f"{MARKET}/datasets", json={"dataset": header, "records": []})

    # WP1's schema validates the period, so the request never reaches the service.
    assert refused.status_code == 422
    assert refused.json()["code"] == "validation_error"