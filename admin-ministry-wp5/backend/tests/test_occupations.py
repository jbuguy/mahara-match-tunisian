import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app

client = TestClient(app)
BASE = "/api/v1/admin/taxonomy"


def _database_is_up() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _database_is_up(), reason="database not reachable")


def _new_occupation_code() -> str:
    return f"OC-8{uuid.uuid4().hex[:6]}"


def _create_skill(label: str) -> str:
    """A throwaway skill, so requirement lines have something real to point at."""
    code = f"SK-8{uuid.uuid4().hex[:6]}"
    created = client.post(
        f"{BASE}/skills", json={"code": code, "label_fr": label, "skill_type": "hard"}
    )
    assert created.status_code == 201
    return code


def _create_occupation(title: str = "Soudeur") -> str:
    code = _new_occupation_code()
    created = client.post(
        f"{BASE}/occupations", json={"code": code, "title_fr": title, "isco_code": "7212"}
    )
    assert created.status_code == 201
    assert created.json()["status"] == "draft"
    return code


@needs_db
def test_create_then_find_an_occupation():
    code = _create_occupation("Soudeur")

    duplicate = client.post(
        f"{BASE}/occupations", json={"code": code, "title_fr": "Soudeur"}
    )
    assert duplicate.status_code == 409

    listed = client.get(f"{BASE}/occupations", params={"search": code})
    assert [item["code"] for item in listed.json()["items"]] == [code]


@needs_db
def test_edit_validate_then_retire_an_occupation():
    code = _create_occupation("Soudur")

    fixed = client.patch(f"{BASE}/occupations/{code}", json={"title_fr": "Soudeur"})
    assert fixed.status_code == 200
    assert fixed.json()["title_fr"] == "Soudeur"

    promoted = client.post(f"{BASE}/occupations/{code}/validate")
    assert promoted.json()["status"] == "validated"

    # Validated, therefore possibly referenced by offers: retired, never erased.
    retired = client.delete(f"{BASE}/occupations/{code}")
    assert retired.json()["outcome"] == "deprecated"
    assert client.get(f"{BASE}/occupations/{code}").json()["status"] == "deprecated"


@needs_db
def test_unused_draft_is_really_deleted_with_its_requirement_lines():
    code = _create_occupation("Erreur de saisie")
    skill = _create_skill("Lecture de plan")
    client.put(
        f"{BASE}/occupations/{code}/skills",
        json={"skills": [{"skill_code": skill, "requirement": "required"}]},
    )

    removed = client.delete(f"{BASE}/occupations/{code}")
    assert removed.json()["outcome"] == "deleted"
    assert client.get(f"{BASE}/occupations/{code}").status_code == 404


@needs_db
def test_required_skills_are_replaced_not_appended():
    code = _create_occupation("Menuisier")
    first = _create_skill("Lecture de plan")
    second = _create_skill("Assemblage bois")

    filled = client.put(
        f"{BASE}/occupations/{code}/skills",
        json={
            "skills": [
                {"skill_code": first, "requirement": "required"},
                {"skill_code": second, "requirement": "preferred"},
            ]
        },
    )
    assert filled.status_code == 200
    assert {line["skill_code"] for line in filled.json()["skills"]} == {first, second}

    # PUT replaces: what you omit is removed.
    trimmed = client.put(
        f"{BASE}/occupations/{code}/skills",
        json={"skills": [{"skill_code": first, "requirement": "required"}]},
    )
    assert [line["skill_code"] for line in trimmed.json()["skills"]] == [first]

    cleared = client.put(f"{BASE}/occupations/{code}/skills", json={"skills": []})
    assert cleared.json()["skills"] == []


@needs_db
def test_a_refused_requirement_list_changes_nothing():
    code = _create_occupation("Caissier")
    skill = _create_skill("Encaissement")

    unknown = client.put(
        f"{BASE}/occupations/{code}/skills",
        json={"skills": [{"skill_code": "SK-999999", "requirement": "required"}]},
    )
    assert unknown.status_code == 404

    duplicated = client.put(
        f"{BASE}/occupations/{code}/skills",
        json={
            "skills": [
                {"skill_code": skill, "requirement": "required"},
                {"skill_code": skill, "requirement": "preferred"},
            ]
        },
    )
    assert duplicated.status_code == 409

    # Neither refusal left a trace.
    assert client.get(f"{BASE}/occupations/{code}").json()["skills"] == []


@needs_db
def test_an_unknown_sector_is_refused():
    refused = client.post(
        f"{BASE}/occupations",
        json={
            "code": _new_occupation_code(),
            "title_fr": "Agent de securite",
            "sector_code": "SEC-999999",
        },
    )
    assert refused.status_code == 404