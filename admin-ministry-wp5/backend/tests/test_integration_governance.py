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


def _seed_suggestion(label: str) -> tuple[uuid.UUID, str]:
    """Stands in for WP2's parsing pipeline, which is not running yet."""
    tag = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        suggestion = SkillSuggestion(
            proposed_label=f"{label} {tag}",
            normalized_label=f"{label.lower().replace(' ', '_')}_{tag}",
            skill_type=SkillType.HARD,
            source=IngestionSource.CV_UPLOAD,
            occurrences=4,
        )
        db.add(suggestion)
        db.commit()
        return suggestion.id, suggestion.proposed_label


@needs_db
def test_a_label_from_the_field_becomes_a_validated_requirement():
    """The full governance journey: an unknown label ends up required by an occupation."""
    before = client.get(f"{MONITORING}/taxonomy").json()
    validated_before = before["skills"].get("validated", 0)
    pending_before = before["suggestions"].get("pending", 0)
    orphans_before = before["occupations_without_skills"]

    # 1. WP2 parses a CV and meets a label the referential does not know.
    suggestion_id, field_label = _seed_suggestion("Soudure TIG")
    assert client.get(f"{TAXONOMY}/suggestions").json()["total"] == pending_before + 1

    # 2. The admin recognises a real skill and approves it.
    skill_code = f"SK-8{uuid.uuid4().hex[:6]}"
    approved = client.post(
        f"{TAXONOMY}/suggestions/{suggestion_id}/approve",
        json={"code": skill_code, "label_fr": "Soudure TIG", "skill_type": "hard"},
    )
    assert approved.status_code == 201
    assert approved.json()["status"] == "draft"  # approving is not validating
    assert field_label in approved.json()["alt_labels"]  # the field wording survives

    # 3. Validation is the separate act that puts it into circulation.
    promoted = client.post(f"{TAXONOMY}/skills/{skill_code}/validate")
    assert promoted.json()["status"] == "validated"

    # 4. An occupation that requires it.
    occupation_code = f"OC-8{uuid.uuid4().hex[:6]}"
    created = client.post(
        f"{TAXONOMY}/occupations",
        json={"code": occupation_code, "title_fr": "Soudeur", "isco_code": "7212"},
    )
    assert created.status_code == 201

    linked = client.put(
        f"{TAXONOMY}/occupations/{occupation_code}/skills",
        json={"skills": [{"skill_code": skill_code, "requirement": "required"}]},
    )
    assert [line["skill_code"] for line in linked.json()["skills"]] == [skill_code]

    official = client.post(f"{TAXONOMY}/occupations/{occupation_code}/validate")
    assert official.json()["status"] == "validated"

    # 5. The dashboard tells the same story.
    after = client.get(f"{MONITORING}/taxonomy").json()
    assert after["skills"].get("validated", 0) == validated_before + 1
    assert after["suggestions"].get("pending", 0) == pending_before  # the inbox emptied again
    assert after["occupations_without_skills"] == orphans_before  # the new one is not an orphan