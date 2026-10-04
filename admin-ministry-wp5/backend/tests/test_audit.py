import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from mahara_data.db.models.taxonomy import SkillSuggestion
from mahara_data.enums import IngestionSource, SkillType

from app.db import SessionLocal, engine
from app.main import app

client = TestClient(app)
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


def _seed_suggestion(label: str) -> uuid.UUID:
    tag = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        suggestion = SkillSuggestion(
            proposed_label=f"{label} {tag}",
            normalized_label=f"{label.lower().replace(' ', '_')}_{tag}",
            skill_type=SkillType.HARD,
            source=IngestionSource.CV_UPLOAD,
        )
        db.add(suggestion)
        db.commit()
        return suggestion.id


def _trail(entity_id: str) -> list[dict]:
    return client.get(f"{MONITORING}/audit", params={"entity_id": entity_id}).json()["items"]


@needs_db
def test_validating_a_skill_leaves_a_trace():
    code = _create_skill("Soudure")
    client.post(f"{TAXONOMY}/skills/{code}/validate")

    entries = _trail(code)
    assert len(entries) == 1
    assert entries[0]["action"] == "skill.validated"
    assert entries[0]["entity_type"] == "skill"
    assert entries[0]["actor_service"] == "wp5-admin"
    assert entries[0]["actor_user_id"] is None  # filled once authentication lands


@needs_db
def test_the_trail_reads_the_whole_life_backwards():
    code = _create_skill("Carrelage")
    client.post(f"{TAXONOMY}/skills/{code}/validate")
    client.delete(f"{TAXONOMY}/skills/{code}")  # validated, so retired rather than erased

    entries = _trail(code)
    assert [entry["action"] for entry in entries] == ["skill.deprecated", "skill.validated"]
    # The trace records the state the entry was leaving, not the one it reached.
    assert entries[0]["payload"]["previous_status"] == "validated"


@needs_db
def test_an_approval_links_the_suggestion_to_the_skill_it_created():
    suggestion_id = _seed_suggestion("Soudure TIG")
    code = f"SK-8{uuid.uuid4().hex[:6]}"

    client.post(
        f"{TAXONOMY}/suggestions/{suggestion_id}/approve",
        json={"code": code, "label_fr": "Soudure TIG", "skill_type": "hard"},
    )

    entries = _trail(str(suggestion_id))
    assert entries[0]["action"] == "suggestion.approved"
    assert entries[0]["payload"]["created_skill_code"] == code


@needs_db
def test_a_refused_act_leaves_no_trace():
    occupation_code = f"OC-8{uuid.uuid4().hex[:6]}"
    client.post(
        f"{TAXONOMY}/occupations", json={"code": occupation_code, "title_fr": "Soudeur"}
    )

    refused = client.put(
        f"{TAXONOMY}/occupations/{occupation_code}/skills",
        json={"skills": [{"skill_code": "SK-999999", "requirement": "required"}]},
    )
    assert refused.status_code == 404

    # No act, no trace. The journal must never record an intention.
    assert _trail(occupation_code) == []