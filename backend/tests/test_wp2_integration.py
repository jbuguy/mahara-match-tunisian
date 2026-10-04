import sys
import tempfile
import types
import uuid
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from mahara_data.db.models.candidates import ConversationSession

from app.database import Base
from app.models import Candidate, CandidateOnboardingSession, User
from app import wp2_integration
from app.wp2_integration import QUESTIONS, create_wp2_router


@pytest.fixture
def wp2_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    ConversationSession.__table__.create(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as db:
        user = User(email="candidate@example.com", roles=["candidate"])
        other_user = User(email="other@example.com", roles=["candidate"])
        db.add_all([user, other_user])
        db.commit()
        db.refresh(user)
        db.refresh(other_user)
        user_id = user.id
        other_user_id = other_user.id

    active_user_id = {"value": user_id}

    def get_db():
        with session_factory() as db:
            yield db

    def get_current_user():
        with session_factory() as db:
            return db.get(User, active_user_id["value"])

    app = FastAPI()
    app.include_router(create_wp2_router(get_db, get_current_user))
    with TestClient(app) as client:
        yield client, session_factory, active_user_id, user_id, other_user_id, monkeypatch
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_creates_and_resumes_user_owned_session(wp2_client):
    client, _session_factory, active_user, user_id, other_user_id, _monkeypatch = wp2_client

    created = client.post("/api/v1/onboarding/sessions")

    assert created.status_code == 201
    payload = created.json()
    assert payload["question"]["id"] == QUESTIONS[0]["id"]
    resumed = client.get(f"/api/v1/onboarding/sessions/{payload['session_id']}")
    assert resumed.status_code == 200
    assert resumed.json()["question"]["id"] == QUESTIONS[0]["id"]

    active_user["value"] = other_user_id
    hidden = client.get(f"/api/v1/onboarding/sessions/{payload['session_id']}")
    assert hidden.status_code == 404
    assert user_id != other_user_id


def test_voice_answers_advance_and_persist_without_saving_audio(wp2_client, tmp_path):
    client, session_factory, _active_user, _user_id, _other_user_id, monkeypatch = wp2_client
    fake_stt = types.ModuleType("mahara_wp2.stt_adapter")
    fake_stt.transcrire_et_extraire = lambda _path, _kind: {
        "texte_brut": "نجار",
        "valeur_extraite": "نجار",
    }
    monkeypatch.setitem(sys.modules, "mahara_wp2.stt_adapter", fake_stt)
    real_temporary_directory = tempfile.TemporaryDirectory

    def temporary_directory(prefix):
        return real_temporary_directory(prefix=prefix, dir=tmp_path)

    monkeypatch.setattr(wp2_integration.tempfile, "TemporaryDirectory", temporary_directory)
    session_id = client.post("/api/v1/onboarding/sessions").json()["session_id"]

    for index, question in enumerate(QUESTIONS):
        response = client.post(
            f"/api/v1/onboarding/sessions/{session_id}/reponse",
            files={"audio": ("answer.wav", b"wav-data", "audio/wav")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["termine"] is (index == len(QUESTIONS) - 1)
        if index < len(QUESTIONS) - 1:
            assert body["question_suivante"]["id"] == QUESTIONS[index + 1]["id"]

    with session_factory() as db:
        saved = db.query(CandidateOnboardingSession).filter_by(id=uuid.UUID(session_id)).one()
        assert saved.status == "completed"
        assert saved.answers["metier"] == "نجار"
    assert not list(tmp_path.iterdir())
    completed = client.get(f"/api/v1/onboarding/sessions/{session_id}").json()
    assert completed["answers"]["metier"] == "نجار"


def test_empty_audio_is_retryable_and_does_not_advance(wp2_client):
    client, _session_factory, _active_user, _user_id, _other_user_id, _monkeypatch = wp2_client
    session_id = client.post("/api/v1/onboarding/sessions").json()["session_id"]

    response = client.post(
        f"/api/v1/onboarding/sessions/{session_id}/reponse",
        files={"audio": ("empty.wav", b"", "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "audio_vide"
    current = client.get(f"/api/v1/onboarding/sessions/{session_id}")
    assert current.json()["question"]["id"] == QUESTIONS[0]["id"]


def test_finalize_links_completed_intake_to_consented_candidate(wp2_client):
    client, session_factory, _active_user, user_id, _other_user_id, _monkeypatch = wp2_client
    session_id = client.post("/api/v1/onboarding/sessions").json()["session_id"]

    with session_factory() as db:
        intake = db.get(CandidateOnboardingSession, uuid.UUID(session_id))
        intake.answers = {question["colonne_csv"]: "Réponse" for question in QUESTIONS}
        intake.status = "completed"
        candidate = Candidate(
            user_id=user_id,
            onboarding_path="derja_detailed",
            literacy_level="literate",
            consent_given_at=datetime.now(UTC),
        )
        db.add(candidate)
        db.commit()
        candidate_id = candidate.id

    response = client.post(f"/api/v1/onboarding/sessions/{session_id}/finalize")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "session_id": session_id,
        "candidate_id": str(candidate_id),
        "onboarding_path": "derja_detailed",
        "status": "linked",
    }
    with session_factory() as db:
        conversation = db.get(ConversationSession, uuid.UUID(session_id))
        assert conversation.candidate_id == candidate_id
        assert conversation.channel.value == "audio"
        assert conversation.transcript == []
        assert db.get(CandidateOnboardingSession, uuid.UUID(session_id)).status == "completed"


def test_finalize_requires_a_saved_consented_profile(wp2_client):
    client, _session_factory, _active_user, _user_id, _other_user_id, _monkeypatch = wp2_client
    session_id = client.post("/api/v1/onboarding/sessions").json()["session_id"]

    response = client.post(f"/api/v1/onboarding/sessions/{session_id}/finalize")

    assert response.status_code == 409


def test_finalize_is_idempotent_for_non_literate_candidate(wp2_client):
    client, session_factory, _active_user, user_id, _other_user_id, _monkeypatch = wp2_client
    session_id = client.post("/api/v1/onboarding/sessions").json()["session_id"]

    with session_factory() as db:
        intake = db.get(CandidateOnboardingSession, uuid.UUID(session_id))
        intake.answers = {question["colonne_csv"]: "Réponse" for question in QUESTIONS}
        intake.status = "completed"
        candidate = Candidate(
            user_id=user_id,
            onboarding_path="derja_detailed",
            literacy_level="non_literate",
            consent_given_at=datetime.now(UTC),
        )
        db.add(candidate)
        db.commit()
        candidate_id = candidate.id

    first = client.post(f"/api/v1/onboarding/sessions/{session_id}/finalize")
    second = client.post(f"/api/v1/onboarding/sessions/{session_id}/finalize")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert second.json()["onboarding_path"] == "derja_guided_voice"
    with session_factory() as db:
        conversation = db.get(ConversationSession, uuid.UUID(session_id))
        assert conversation.candidate_id == candidate_id
        assert conversation.onboarding_path.value == "derja_guided_voice"