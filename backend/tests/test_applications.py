import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.applications import create_application_router
from mahara_data.db import Base
from mahara_data.db.models.accounts import User
from mahara_data.db.models.candidates import Candidate
from mahara_data.db.models.employers import Application, Employer, JobOffer, HiringFeedback
from mahara_data.db.models.matching import MatchResult
from mahara_data.db.models.reference import Governorate
from mahara_data.enums import (
    ApplicationStatus,
    ContractType,
    HiringDecision,
    LiteracyLevel,
    OfferSource,
    OfferStatus,
    OnboardingPath,
    UserRole,
    WorkMode,
    CompanySize,
)


@pytest.fixture
def application_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    candidate_user_id = uuid.uuid4()
    employer_user_id = uuid.uuid4()
    other_employer_user_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()
    other_employer_id = uuid.uuid4()
    offer_id = uuid.uuid4()
    match_id = uuid.uuid4()
    current_user = {"value": type("UserRef", (), {"id": candidate_user_id})()}
    current_employer = {"value": type("EmployerRef", (), {"id": employer_id})()}

    with sessions() as db:
        db.add_all(
            [
                User(id=candidate_user_id, role=UserRole.CANDIDATE, email="candidate@test.local"),
                User(id=employer_user_id, role=UserRole.EMPLOYER, email="employer@test.local"),
                User(id=other_employer_user_id, role=UserRole.EMPLOYER, email="other@test.local"),
                Governorate(code="TN-11", name_fr="Tunis", name_ar="تونس"),
            ]
        )
        db.flush()
        db.add_all(
            [
                Candidate(
                    id=candidate_id,
                    user_id=candidate_user_id,
                    onboarding_path=OnboardingPath.CV_UPLOAD,
                    literacy_level=LiteracyLevel.LITERATE,
                ),
                Employer(
                    id=employer_id,
                    user_id=employer_user_id,
                    company_name="Employer",
                    email="employer@test.local",
                    password_hash="unused",
                    sector="Technology",
                    company_size=CompanySize.SMALL,
                ),
                Employer(
                    id=other_employer_id,
                    user_id=other_employer_user_id,
                    company_name="Other Employer",
                    email="other@test.local",
                    password_hash="unused",
                    sector="Technology",
                    company_size=CompanySize.SMALL,
                ),
                JobOffer(
                    id=offer_id,
                    employer_id=employer_id,
                    title="Developer",
                    description_raw="Build software.",
                    contract_type=ContractType.CDI,
                    work_mode=WorkMode.ON_SITE,
                    governorate_code="TN-11",
                    status=OfferStatus.PUBLISHED,
                    source=OfferSource.EMPLOYER_FORM,
                    positions_count=1,
                    min_years_experience=0,
                    languages_required=[],
                ),
                MatchResult(
                    id=match_id,
                    candidate_id=candidate_id,
                    job_offer_id=offer_id,
                    score_global=80,
                    score_hard_skills=80,
                    score_experience=100,
                    score_soft_skills=100,
                    score_location=100,
                    weights={"hard_skills": 0.5, "experience": 0.2, "soft_skills": 0.15, "location": 0.15},
                    model_version="test-v1",
                    is_current=True,
                ),
            ]
        )
        db.commit()

    def get_db():
        with sessions() as db:
            yield db

    def get_current_user():
        return current_user["value"]

    def get_current_employer():
        return current_employer["value"]

    app = FastAPI()
    app.include_router(create_application_router(get_db, get_current_user, get_current_employer))
    with TestClient(app) as client:
        yield client, sessions, current_user, current_employer, candidate_id, employer_id, other_employer_id, offer_id
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_candidate_applies_once_to_currently_matched_offer(application_client):
    client, sessions, _user, _employer, candidate_id, _employer_id, _other_id, offer_id = application_client

    created = client.post("/api/v1/me/applications", json={"job_offer_id": str(offer_id), "cover_note": "Bonjour"})
    duplicate = client.post("/api/v1/me/applications", json={"job_offer_id": str(offer_id)})

    assert created.status_code == 201
    assert created.json()["status"] == ApplicationStatus.SUBMITTED.value
    assert duplicate.status_code == 409
    with sessions() as db:
        application = db.query(Application).one()
        assert application.candidate_id == candidate_id
        assert application.match_result_id is not None


def test_applicant_list_is_employer_scoped_and_excludes_pii(application_client):
    client, _sessions, _user, active_employer, _candidate_id, _employer_id, other_employer_id, offer_id = application_client
    client.post("/api/v1/me/applications", json={"job_offer_id": str(offer_id)})

    own = client.get("/api/v1/employer/applications")
    active_employer["value"] = type("EmployerRef", (), {"id": other_employer_id})()
    other = client.get("/api/v1/employer/applications")

    assert own.status_code == 200
    assert len(own.json()) == 1
    assert "email" not in own.json()[0]
    assert "full_name" not in own.json()[0]
    assert other.json() == []


def test_employer_decision_persists_feedback_and_rejects_other_owner(application_client):
    client, sessions, _user, active_employer, _candidate_id, employer_id, other_employer_id, offer_id = application_client
    created = client.post("/api/v1/me/applications", json={"job_offer_id": str(offer_id)}).json()

    active_employer["value"] = type("EmployerRef", (), {"id": other_employer_id})()
    denied = client.patch(
        f"/api/v1/employer/applications/{created['application_id']}",
        json={"decision": "hired"},
    )
    active_employer["value"] = type("EmployerRef", (), {"id": employer_id})()
    decided = client.patch(
        f"/api/v1/employer/applications/{created['application_id']}",
        json={"decision": "shortlisted", "match_quality": 4, "comment": "Strong fit"},
    )

    assert denied.status_code == 404
    assert decided.status_code == 200
    assert decided.json()["status"] == ApplicationStatus.SHORTLISTED.value
    with sessions() as db:
        assert db.query(HiringFeedback).one().decision is HiringDecision.SHORTLISTED


def test_candidate_application_list_is_scoped_to_own_profile(application_client):
    client, _sessions, active_user, _employer, _candidate_id, _employer_id, _other_id, offer_id = application_client
    client.post("/api/v1/me/applications", json={"job_offer_id": str(offer_id)})
    active_user["value"] = type("UserRef", (), {"id": uuid.uuid4()})()

    assert client.get("/api/v1/me/applications").status_code == 404