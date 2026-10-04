import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app

client = TestClient(app)


def _database_is_up() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _database_is_up(), reason="database not reachable")


def _new_code() -> str:
    """A throwaway code in the SK-8xxx development range, unique per run."""
    return f"SK-8{uuid.uuid4().hex[:6]}"


@needs_db
def test_create_then_find_a_skill():
    code = _new_code()
    payload = {"code": code, "label_fr": "Soudure a l'arc", "skill_type": "hard"}

    created = client.post("/api/v1/admin/taxonomy/skills", json=payload)
    assert created.status_code == 201
    assert created.json()["status"] == "draft"

    duplicate = client.post("/api/v1/admin/taxonomy/skills", json=payload)
    assert duplicate.status_code == 409

    listed = client.get("/api/v1/admin/taxonomy/skills", params={"search": code})
    assert listed.status_code == 200
    assert [item["code"] for item in listed.json()["items"]] == [code]


@needs_db
def test_edit_validate_then_retire_a_skill():
    code = _new_code()
    client.post(
        "/api/v1/admin/taxonomy/skills",
        json={"code": code, "label_fr": "Soudre", "skill_type": "hard"},
    )

    fixed = client.patch(
        f"/api/v1/admin/taxonomy/skills/{code}",
        json={"label_fr": "Soudure", "label_derja": "soudure"},
    )
    assert fixed.status_code == 200
    assert fixed.json()["label_fr"] == "Soudure"
    assert fixed.json()["version"] == 2

    promoted = client.post(f"/api/v1/admin/taxonomy/skills/{code}/validate")
    assert promoted.status_code == 200
    assert promoted.json()["status"] == "validated"

    # Validated, therefore possibly in use: it must be retired, never erased.
    retired = client.delete(f"/api/v1/admin/taxonomy/skills/{code}")
    assert retired.status_code == 200
    assert retired.json()["outcome"] == "deprecated"

    assert client.get(f"/api/v1/admin/taxonomy/skills/{code}").json()["status"] == "deprecated"


@needs_db
def test_unused_draft_is_really_deleted():
    code = _new_code()
    client.post(
        "/api/v1/admin/taxonomy/skills",
        json={"code": code, "label_fr": "Erreur de saisie", "skill_type": "hard"},
    )

    removed = client.delete(f"/api/v1/admin/taxonomy/skills/{code}")
    assert removed.json()["outcome"] == "deleted"
    assert client.get(f"/api/v1/admin/taxonomy/skills/{code}").status_code == 404