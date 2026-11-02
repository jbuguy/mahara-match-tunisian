import json
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.features.employee.auth import get_current_user
from app.features.employee.data_lifecycle import (
    DELETION_RETENTION_DAYS,
    build_candidate_export,
    purge_expired_candidate_accounts,
    request_candidate_deletion,
)
from app.models import AccountActionToken, CandidateOnboardingSession
from mahara_data.db import Base as SharedBase
from mahara_data.db.models.accounts import AuthIdentity, User
from mahara_data.db.models.candidates import Candidate, CandidateExperience, CandidatePII


@pytest.fixture
def lifecycle_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SharedBase.metadata.create_all(engine)
    AccountActionToken.__table__.create(engine)
    CandidateOnboardingSession.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as db:
        yield db
    CandidateOnboardingSession.__table__.drop(engine)
    AccountActionToken.__table__.drop(engine)
    SharedBase.metadata.drop_all(engine)
    engine.dispose()


def create_candidate(db):
    user = User(email="candidate@example.com", phone="+21620123456", role="candidate")
    db.add(user)
    db.flush()
    candidate = Candidate(
        user_id=user.id,
        onboarding_path="derja_detailed",
        literacy_level="literate",
        summary="Personal summary",
        raw_profile={"name": "Sensitive raw profile"},
    )
    db.add(candidate)
    db.flush()
    db.add(
        CandidatePII(
            candidate_id=candidate.id,
            full_name="Candidate Name",
            email=user.email,
            phone=user.phone,
            address="Private address",
            photo=b"jpeg",
        )
    )
    db.add(CandidateExperience(candidate_id=candidate.id, job_title_raw="Mason", employer_name="Private employer"))
    db.commit()
    return user, candidate


def test_export_contains_candidate_json_and_photo_without_credentials(lifecycle_session):
    db = lifecycle_session
    user, _candidate = create_candidate(db)
    user.password_hash = "never-export-this-hash"
    db.commit()

    archive_file = build_candidate_export(db, user)
    try:
        with zipfile.ZipFile(archive_file) as archive:
            assert set(archive.namelist()) == {"data.json", "candidate/photo.jpg"}
            data = json.loads(archive.read("data.json"))
            assert archive.read("candidate/photo.jpg") == b"jpeg"
    finally:
        archive_file.close()

    assert data["account"]["email"] == "candidate@example.com"
    assert "password_hash" not in data["account"]
    assert data["candidate_pii"]["full_name"] == "Candidate Name"
    assert data["experiences"][0]["employer_name"] == "Private employer"


def test_deletion_deactivates_and_redacts_candidate_identifiers(lifecycle_session, monkeypatch):
    db = lifecycle_session
    user, candidate = create_candidate(db)
    db.add(
        AuthIdentity(
            user_id=user.id,
            provider="google",
            provider_user_id="google-subject",
            email=user.email,
        )
    )
    db.add(
        AccountActionToken(
            user_id=user.id,
            token_hash="a" * 64,
            purpose="password_reset",
            expires_at=datetime.now(UTC),
        )
    )
    db.commit()
    monkeypatch.setattr("app.features.employee.data_lifecycle._delete_private_object", lambda _key: None)

    purge_after = request_candidate_deletion(db, user)
    db.refresh(user)
    db.refresh(candidate)
    pii = db.get(CandidatePII, candidate.id)
    experience = db.query(CandidateExperience).filter_by(candidate_id=candidate.id).one()

    assert user.is_active is False
    assert user.email == f"deleted-{user.id}@example.invalid"
    assert user.phone is None
    assert user.password_hash is None
    assert user.deletion_requested_at is not None
    assert candidate.deleted_at is not None
    assert candidate.summary is None
    assert candidate.raw_profile is None
    assert pii.full_name is None and pii.email is None and pii.phone is None and pii.photo is None
    assert experience.employer_name is None
    assert db.query(AuthIdentity).count() == 0
    assert db.query(AccountActionToken).count() == 0
    requested_at = user.deletion_requested_at.replace(tzinfo=UTC)
    assert (purge_after - requested_at).days == DELETION_RETENTION_DAYS


def test_employee_auth_rejects_inactive_and_unknown_accounts(lifecycle_session):
    db = lifecycle_session
    user, _candidate = create_candidate(db)
    claims = {"email": user.email}

    assert get_current_user(claims=claims, db=db).user.id == user.id
    user.is_active = False
    db.commit()
    with pytest.raises(HTTPException) as inactive:
        get_current_user(claims=claims, db=db)
    assert inactive.value.status_code == 401

    with pytest.raises(HTTPException) as missing:
        get_current_user(claims={"email": "missing@example.com"}, db=db)
    assert missing.value.status_code == 401


def test_deletion_rejects_multi_role_accounts(lifecycle_session):
    db = lifecycle_session
    user, _candidate = create_candidate(db)
    user.roles = ["candidate", "employer"]
    db.commit()

    with pytest.raises(HTTPException) as forbidden:
        request_candidate_deletion(db, user)
    assert forbidden.value.status_code == 403
    assert user.is_active is True


def test_purge_removes_candidate_and_account_after_retention(lifecycle_session, monkeypatch):
    db = lifecycle_session
    user, candidate = create_candidate(db)
    expired_at = datetime.now(UTC) - timedelta(days=DELETION_RETENTION_DAYS + 1)
    user.deletion_requested_at = expired_at
    candidate.deleted_at = expired_at
    user_id = user.id
    candidate_id = candidate.id
    db.commit()
    session_factory = sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)
    monkeypatch.setattr("app.database.SessionLocal", session_factory)
    monkeypatch.setattr("app.features.employee.data_lifecycle._delete_private_object", lambda _key: None)

    assert purge_expired_candidate_accounts(now=datetime.now(UTC)) == 1
    db.expire_all()
    assert db.get(User, user_id) is None
    assert db.get(Candidate, candidate_id) is None
    assert db.get(CandidatePII, candidate_id) is None
