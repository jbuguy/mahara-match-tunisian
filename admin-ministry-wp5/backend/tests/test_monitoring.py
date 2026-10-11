import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app

client = TestClient(app)
MONITORING = "/api/v1/admin/monitoring"
TAXONOMY = "/api/v1/admin/taxonomy"


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


@needs_db
def test_overview_reports_the_module_and_its_database():
    body = client.get(f"{MONITORING}/overview").json()

    assert body["module"] == "wp5-admin-ministry"
    assert body["database_latency_ms"] is not None  # the probe reached Postgres
    assert body["uptime_seconds"] >= 0


@needs_db
def test_traffic_counters_grow_with_traffic():
    before = client.get(f"{MONITORING}/overview").json()["requests_total"]

    client.get("/api/v1/health")
    client.get("/api/v1/health")

    after = client.get(f"{MONITORING}/overview").json()["requests_total"]
    # The two health calls, plus the overview call that read `before`.
    assert after >= before + 3


@needs_db
def test_routes_are_counted_by_template_never_by_id():
    first = _create_skill("Soudure")
    second = _create_skill("Peinture")

    client.get(f"{TAXONOMY}/skills/{first}")
    client.get(f"{TAXONOMY}/skills/{second}")

    labels = [row["route"] for row in client.get(f"{MONITORING}/routes").json()]

    # One bucket for both reads...
    assert any(label.endswith("/admin/taxonomy/skills/{code}") for label in labels)
    # ...and no skill code ever leaks into a metric name.
    assert not any(first in label or second in label for label in labels)


@needs_db
def test_taxonomy_stats_follow_the_referential():
    before = client.get(f"{MONITORING}/taxonomy").json()["skills"].get("draft", 0)

    _create_skill("Carrelage")

    after = client.get(f"{MONITORING}/taxonomy").json()["skills"].get("draft", 0)
    assert after == before + 1