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


@needs_db
def test_create_then_find_a_skill():
    code = f"SK-8{uuid.uuid4().int % 1000:03d}"
    payload = {"code": code, "label_fr": "Soudure a l'arc", "skill_type": "hard"}

    created = client.post("/api/v1/admin/taxonomy/skills", json=payload)
    assert created.status_code == 201
    assert created.json()["status"] == "draft"

    duplicate = client.post("/api/v1/admin/taxonomy/skills", json=payload)
    assert duplicate.status_code == 409

    listed = client.get("/api/v1/admin/taxonomy/skills", params={"search": code})
    assert listed.status_code == 200
    assert [item["code"] for item in listed.json()["items"]] == [code]