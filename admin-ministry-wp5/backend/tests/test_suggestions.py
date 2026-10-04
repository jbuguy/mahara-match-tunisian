import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from mahara_data.db.models.taxonomy import SkillSuggestion
from mahara_data.enums import IngestionSource, SkillType, SuggestionStatus

from app.db import SessionLocal, engine
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


def _new_code() -> str:
    """A throwaway code in the SK-8xxx development range, unique per run."""
    return f"SK-8{uuid.uuid4().hex[:6]}"


def _seed_suggestion(label: str, *, occurrences: int = 1) -> tuple[uuid.UUID, str]:
    """WP2's pipeline writes these rows. Until it runs, the test plays its part."""
    tag = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        suggestion = SkillSuggestion(
            proposed_label=f"{label} {tag}",
            normalized_label=f"{label.lower().replace(' ', '_')}_{tag}",
            skill_type=SkillType.HARD,
            source=IngestionSource.CV_UPLOAD,
            occurrences=occurrences,
        )
        db.add(suggestion)
        db.commit()
        return suggestion.id, suggestion.proposed_label


def _review_state(suggestion_id: uuid.UUID) -> tuple[SuggestionStatus, uuid.UUID | None]:
    """No read-by-id route exists, so the test checks the row itself."""
    with SessionLocal() as db:
        row = db.get(SkillSuggestion, suggestion_id)
        return row.status, row.resolved_skill_id


@needs_db
def test_approve_creates_a_draft_and_keeps_the_field_label():
    suggestion_id, field_label = _seed_suggestion("Soudure TIG")
    code = _new_code()

    created = client.post(
        f"{BASE}/suggestions/{suggestion_id}/approve",
        json={"code": code, "label_fr": "Soudure TIG", "skill_type": "hard"},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "draft"
    # The wording found in the field survives, so the pipelines recognise it next time.
    assert field_label in created.json()["alt_labels"]

    status, resolved_skill_id = _review_state(suggestion_id)
    assert status == SuggestionStatus.APPROVED
    assert resolved_skill_id is not None

    # A verdict applies once: a second admin clicking later gets a conflict.
    again = client.post(
        f"{BASE}/suggestions/{suggestion_id}/approve",
        json={"code": _new_code(), "label_fr": "Soudure TIG", "skill_type": "hard"},
    )
    assert again.status_code == 409


@needs_db
def test_merge_turns_the_label_into_a_synonym():
    code = _new_code()
    client.post(
        f"{BASE}/skills",
        json={"code": code, "label_fr": "Menuiserie", "skill_type": "hard"},
    )
    suggestion_id, field_label = _seed_suggestion("Menuisier")

    merged = client.post(f"{BASE}/suggestions/{suggestion_id}/merge", json={"code": code})
    assert merged.status_code == 200
    assert field_label in merged.json()["alt_labels"]
    assert merged.json()["version"] == 2  # a shared referential tracks its edits

    status, resolved_skill_id = _review_state(suggestion_id)
    assert status == SuggestionStatus.MERGED
    assert resolved_skill_id is not None


@needs_db
def test_merge_into_an_unknown_skill_is_refused():
    suggestion_id, _ = _seed_suggestion("Plomberie")

    missed = client.post(
        f"{BASE}/suggestions/{suggestion_id}/merge", json={"code": "SK-999999"}
    )
    assert missed.status_code == 404
    # The suggestion must still be waiting: a failed verdict changes nothing.
    assert _review_state(suggestion_id)[0] == SuggestionStatus.PENDING


@needs_db
def test_reject_records_the_refusal():
    suggestion_id, _ = _seed_suggestion("Motive et dynamique")

    rejected = client.post(f"{BASE}/suggestions/{suggestion_id}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    status, resolved_skill_id = _review_state(suggestion_id)
    assert status == SuggestionStatus.REJECTED
    assert resolved_skill_id is None


@needs_db
def test_inbox_puts_the_busiest_labels_first():
    rare, _ = _seed_suggestion("Calligraphie", occurrences=2)
    common, _ = _seed_suggestion("Caisse enregistreuse", occurrences=999)

    inbox = client.get(f"{BASE}/suggestions", params={"page_size": 200})
    assert inbox.status_code == 200
    ids = [item["suggestion_id"] for item in inbox.json()["items"]]
    assert ids.index(str(common)) < ids.index(str(rare))