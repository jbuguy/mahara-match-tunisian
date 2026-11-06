import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.applications import create_application_router
from app.features.employer.dashboard import create_employer_dashboard_router
from app.models import EmployerDraftSession
from mahara_data.db import Base
from mahara_data.db.models.accounts import User
from mahara_data.db.models.candidates import Candidate, CandidatePII
from mahara_data.db.models.employers import Application, Employer, JobOffer, HiringFeedback
from mahara_data.db.models.matching import MatchResult
from mahara_data.db.models.platform import NotificationOutbox
from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Skill
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
    SkillType,
    TaxonomyStatus,
)


@pytest.fixture
def application_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    EmployerDraftSession.__table__.create(bind=engine, checkfirst=True)
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
    app.include_router(create_employer_dashboard_router(get_db, get_current_employer))
    with TestClient(app) as client:
        yield client, sessions, current_user, current_employer, candidate_id, employer_id, other_employer_id, offer_id
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_candidate_applies_once_to_currently_matched_offer(application_client):
    client, sessions, _user, _employer, candidate_id, _employer_id, _other_id, offer_id = application_client

    created = client.post("/api/v1/me/applications", json={"job_offer_id": str(offer_id), "cover_note": "Bonjour", "employer_contact_consent": True})
    duplicate = client.post("/api/v1/me/applications", json={"job_offer_id": str(offer_id), "employer_contact_consent": True})

    assert created.status_code == 201
    assert created.json()["status"] == ApplicationStatus.SUBMITTED.value
    assert duplicate.status_code == 409
    with sessions() as db:
        application = db.query(Application).one()
        assert application.candidate_id == candidate_id
        assert application.match_result_id is not None


def test_applicant_list_is_employer_scoped_and_excludes_pii(application_client):
    client, _sessions, _user, active_employer, _candidate_id, _employer_id, other_employer_id, offer_id = application_client
    client.post("/api/v1/me/applications", json={"job_offer_id": str(offer_id), "employer_contact_consent": True})

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
    created = client.post("/api/v1/me/applications", json={"job_offer_id": str(offer_id), "employer_contact_consent": True}).json()

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


def test_repeated_identical_employer_decision_is_idempotent(application_client):
    client, sessions, _user, _active_employer, _candidate_id, _employer_id, _other_id, offer_id = application_client
    application = client.post(
        "/api/v1/me/applications",
        json={"job_offer_id": str(offer_id), "employer_contact_consent": True},
    ).json()
    url = f"/api/v1/employer/applications/{application['application_id']}"

    first = client.patch(url, json={"decision": "shortlisted"})
    repeated = client.patch(url, json={"decision": "shortlisted"})

    assert first.status_code == repeated.status_code == 200
    assert first.json() == repeated.json()
    with sessions() as db:
        assert db.query(HiringFeedback).count() == 1


def test_employer_application_filters_return_paginated_shape(application_client):
    client, sessions, _user, _active_employer, _candidate_id, _employer_id, _other_id, offer_id = application_client
    created = client.post(
        "/api/v1/me/applications",
        json={"job_offer_id": str(offer_id), "employer_contact_consent": True},
    ).json()
    other_candidate_id = uuid.uuid4()
    other_match_id = uuid.uuid4()
    other_application_id = uuid.uuid4()
    with sessions() as db:
        db.add(
            Candidate(
                id=other_candidate_id,
                onboarding_path=OnboardingPath.CV_UPLOAD,
                literacy_level=LiteracyLevel.LITERATE,
            )
        )
        db.add(
            MatchResult(
                id=other_match_id,
                candidate_id=other_candidate_id,
                job_offer_id=offer_id,
                score_global=85,
                score_hard_skills=85,
                score_experience=85,
                score_soft_skills=85,
                score_location=85,
                weights={"hard_skills": 0.5},
                model_version="test-v1",
                is_current=True,
            )
        )
        db.add(
            Application(
                id=other_application_id,
                candidate_id=other_candidate_id,
                job_offer_id=offer_id,
                match_result_id=other_match_id,
                status=ApplicationStatus.SHORTLISTED,
                employer_contact_consent_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    response = client.get(
        "/api/v1/employer/applications",
        params=[
            ("offer_id", str(offer_id)),
            ("status", "submitted"),
            ("status", "shortlisted"),
            ("min_score", "75"),
            ("sort", "applied_at"),
            ("limit", "1"),
        ],
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["next_page"] == 2
    assert response.json()["items"][0]["application_id"] in {
        created["application_id"],
        str(other_application_id),
    }
    assert response.json()["items"][0]["offer_title"] == "Developer"
    assert response.json()["items"][0]["gaps_summary"] == []
    next_page = client.get(
        "/api/v1/employer/applications",
        params=[
            ("offer_id", str(offer_id)),
            ("status", "submitted"),
            ("status", "shortlisted"),
            ("min_score", "75"),
            ("sort", "applied_at"),
            ("page", "2"),
            ("limit", "1"),
        ],
    )
    assert next_page.status_code == 200
    assert next_page.json()["total"] == 2
    assert next_page.json()["next_page"] is None
    assert next_page.json()["items"][0]["application_id"] != response.json()["items"][0]["application_id"]


def test_employer_dashboard_empty_scores_and_employer_scope(application_client):
    client, _sessions, _user, active_employer, _candidate_id, employer_id, other_employer_id, offer_id = application_client
    empty = client.get("/api/v1/employer/dashboard")
    assert empty.status_code == 200
    assert empty.json()["kpis"]["applications_total"] == 0
    assert empty.json()["kpis"]["average_match_score"] is None

    client.post(
        "/api/v1/me/applications",
        json={"job_offer_id": str(offer_id), "employer_contact_consent": True},
    )
    own = client.get("/api/v1/employer/dashboard").json()
    assert own["kpis"]["applications_total"] == 1
    assert own["kpis"]["average_match_score"] == 80

    active_employer["value"] = type("EmployerRef", (), {"id": other_employer_id})()
    other_dashboard = client.get("/api/v1/employer/dashboard").json()
    other_offers = client.get("/api/v1/employer/offers/counts").json()
    other_offer_list = client.get("/api/v1/employer/offers").json()
    other_applications = client.get("/api/v1/employer/applications").json()
    assert other_dashboard["kpis"]["applications_total"] == 0
    assert other_dashboard["kpis"]["average_match_score"] is None
    assert other_dashboard["kpis"]["next_interview_at"] is None
    assert other_dashboard["offers_snapshot"] == []
    assert other_offers == {"all": 0, "published": 0, "drafts": 0, "archived": 0}
    assert other_offer_list == []
    assert other_applications == []
    active_employer["value"] = type("EmployerRef", (), {"id": employer_id})()


def test_dashboard_attention_items_follow_priority_order(application_client):
    client, sessions, _user, _active_employer, candidate_id, employer_id, _other_id, offer_id = application_client
    application = client.post(
        "/api/v1/me/applications",
        json={"job_offer_id": str(offer_id), "employer_contact_consent": True},
    ).json()
    with sessions() as db:
        offer = db.get(JobOffer, offer_id)
        offer.expires_at = datetime.now(timezone.utc) + timedelta(days=6)
        shortlisted_candidate_id = uuid.uuid4()
        shortlisted_match_id = uuid.uuid4()
        shortlisted_application_id = uuid.uuid4()
        db.add(
            Candidate(
                id=shortlisted_candidate_id,
                onboarding_path=OnboardingPath.CV_UPLOAD,
                literacy_level=LiteracyLevel.LITERATE,
            )
        )
        db.add(
            MatchResult(
                id=shortlisted_match_id,
                candidate_id=shortlisted_candidate_id,
                job_offer_id=offer_id,
                score_global=75,
                score_hard_skills=75,
                score_experience=75,
                score_soft_skills=75,
                score_location=75,
                weights={"hard_skills": 0.5},
                model_version="test-v1",
                is_current=True,
            )
        )
        db.add(
            Application(
                id=shortlisted_application_id,
                candidate_id=shortlisted_candidate_id,
                job_offer_id=offer_id,
                match_result_id=shortlisted_match_id,
                status=ApplicationStatus.SHORTLISTED,
                employer_contact_consent_at=datetime.now(timezone.utc),
            )
        )
        db.add(EmployerDraftSession(employer_id=employer_id, state={}, messages=[], draft=None))
        db.commit()

    dashboard = client.get("/api/v1/employer/dashboard").json()

    assert dashboard["kpis"]["applications_total"] == 2
    assert [item["type"] for item in dashboard["attention"]] == [
        "new_applications",
        "shortlisted_without_interview",
        "offers_expiring",
        "unfinished_drafts",
        "profile_readiness",
    ]
    assert dashboard["attention"][0]["sample_ids"] == [application["application_id"]]
    assert client.get("/api/v1/employer/offers/counts").json() == {
        "all": 2,
        "published": 1,
        "drafts": 1,
        "archived": 0,
    }


def test_employer_interviews_are_scoped_and_filtered(application_client):
    client, sessions, _user, active_employer, candidate_id, employer_id, other_employer_id, offer_id = application_client
    application = client.post(
        "/api/v1/me/applications",
        json={"job_offer_id": str(offer_id), "employer_contact_consent": True},
    ).json()
    future = datetime.now(timezone.utc) + timedelta(days=2)
    past = datetime.now(timezone.utc) - timedelta(days=2)
    with sessions() as db:
        db.add(CandidatePII(candidate_id=candidate_id, full_name="Candidate One"))
        db.add_all(
            [
                NotificationOutbox(
                    application_id=uuid.UUID(application["application_id"]),
                    candidate_id=candidate_id,
                    employer_id=employer_id,
                    meeting_at=future,
                    meeting_timezone="Africa/Tunis",
                    recipient_email="candidate@test.local",
                    subject="Interview",
                    body="Interview",
                    status="sent",
                    attempts=1,
                    next_attempt_at=datetime.now(timezone.utc),
                    sent_at=datetime.now(timezone.utc),
                ),
                NotificationOutbox(
                    application_id=uuid.UUID(application["application_id"]),
                    candidate_id=candidate_id,
                    employer_id=employer_id,
                    meeting_at=past,
                    meeting_timezone="Africa/Tunis",
                    recipient_email="candidate@test.local",
                    subject="Interview",
                    body="Interview",
                    status="failed",
                    attempts=1,
                    next_attempt_at=datetime.now(timezone.utc),
                ),
            ]
        )
        db.commit()

    upcoming = client.get("/api/v1/employer/interviews?upcoming=true&status=sent")
    assert upcoming.status_code == 200
    assert len(upcoming.json()) == 1
    assert upcoming.json()[0]["candidate_name"] == "Candidate One"
    assert upcoming.json()[0]["status"] == "sent"
    assert upcoming.json()[0]["meeting_at"].endswith("Z")
    assert client.get("/api/v1/employer/dashboard").json()["kpis"]["next_interview_at"] == (
        future.isoformat().replace("+00:00", "Z")
    )

    active_employer["value"] = type("EmployerRef", (), {"id": other_employer_id})()
    assert client.get("/api/v1/employer/interviews").json() == []
    active_employer["value"] = type("EmployerRef", (), {"id": employer_id})()


def test_interview_creation_rejects_missing_consent_and_past_time(application_client, monkeypatch):
    import app.applications as applications_module
    from types import SimpleNamespace

    client, sessions, _user, _active_employer, candidate_id, _employer_id, _other_id, offer_id = application_client
    application = client.post(
        "/api/v1/me/applications",
        json={"job_offer_id": str(offer_id), "employer_contact_consent": True},
    ).json()
    with sessions() as db:
        row = db.query(Application).one()
        row.status = ApplicationStatus.SHORTLISTED
        row.employer_contact_consent_at = None
        db.add(CandidatePII(candidate_id=candidate_id, email="candidate@test.local"))
        db.commit()
    monkeypatch.setattr(
        applications_module,
        "get_settings",
        lambda: SimpleNamespace(smtp_host="smtp.test", smtp_from_email="noreply@test.local"),
    )
    invitation_url = f"/api/v1/employer/applications/{application['application_id']}/interviews"
    payload = {
        "meeting_at_local": (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat(),
        "timezone": "Africa/Tunis",
    }

    no_consent = client.post(invitation_url, json=payload)
    assert no_consent.status_code == 409
    assert no_consent.json()["detail"]["code"] == "employer_contact_consent_required"

    with sessions() as db:
        row = db.query(Application).one()
        row.employer_contact_consent_at = datetime.now(timezone.utc)
        db.commit()
    payload["meeting_at_local"] = (datetime.now() - timedelta(days=1)).replace(microsecond=0).isoformat()
    past = client.post(invitation_url, json=payload)
    assert past.status_code == 422
    assert past.json()["detail"]["code"] == "meeting_time_in_past"


def test_offer_update_returns_utc_expiry_and_structured_skill_errors(application_client, monkeypatch):
    import app.applications as applications_module

    client, sessions, _user, active_employer, _candidate_id, employer_id, _other_id, offer_id = application_client
    active_employer["value"] = type("EmployerRef", (), {"id": employer_id, "user_id": None})()
    monkeypatch.setattr(
        applications_module,
        "ensure_employer_email_verified",
        lambda db, employer: employer,
    )
    with sessions() as db:
        db.add(
            Skill(
                code="SK-TEST",
                label_fr="Test skill",
                skill_type=SkillType.HARD,
                status=TaxonomyStatus.VALIDATED,
            )
        )
        db.commit()
    expiry = (datetime.now(timezone.utc) + timedelta(days=30)).replace(microsecond=0)
    payload = {
        "offer_id": str(offer_id),
        "employer_id": str(employer_id),
        "title": "Developer",
        "description": "Build and maintain software products.",
        "contract_type": "cdi",
        "work_mode": "on_site",
        "location": {"governorate_code": "TN-11", "delegation": "Tunis"},
        "positions_count": 1,
        "min_years_experience": 0,
        "education_level_min": None,
        "salary": None,
        "skills": [{"skill_code": "SK-TEST", "requirement": "required", "min_level": 1}],
        "languages_required": [{"code": "fr", "level": 3}],
        "expires_at": expiry.isoformat(),
    }

    updated = client.put(f"/api/v1/employer/offers/{offer_id}", json=payload)
    assert updated.status_code == 200, updated.text
    assert updated.json()["expires_at"].endswith("Z") or updated.json()["expires_at"].endswith("+00:00")

    payload["skills"] = [{"skill_code": "UNKNOWN", "requirement": "required", "min_level": 1}]
    invalid_skill = client.put(f"/api/v1/employer/offers/{offer_id}", json=payload)
    assert invalid_skill.status_code == 422
    assert invalid_skill.json()["detail"]["code"] == "invalid_skills"
    assert invalid_skill.json()["detail"]["field"] == "skills"
    assert invalid_skill.json()["detail"]["details"]["invalid_skill_codes"] == ["UNKNOWN"]

    payload["skills"] = [{"skill_code": "SK-TEST", "requirement": "required", "min_level": 1}]
    payload["languages_required"] = [{"code": "fr", "level": 5}]
    invalid_language = client.put(f"/api/v1/employer/offers/{offer_id}", json=payload)
    assert invalid_language.status_code == 422
    assert any("languages_required" in str(error["loc"]) for error in invalid_language.json()["detail"])


def test_reopening_expired_offer_requires_a_future_expiry(application_client):
    client, sessions, _user, _active_employer, _candidate_id, _employer_id, _other_id, offer_id = application_client
    with sessions() as db:
        offer = db.get(JobOffer, offer_id)
        offer.status = OfferStatus.CLOSED
        offer.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    response = client.patch(
        f"/api/v1/employer/offers/{offer_id}/status",
        json={"status": "published"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "expired_offer"


def test_employer_editor_catalogs_are_searchable_and_expose_language_levels(application_client):
    client, sessions, _user, _active_employer, _candidate_id, _employer_id, _other_id, _offer_id = application_client
    with sessions() as db:
        db.add(
            Skill(
                code="SK-CATALOG",
                label_fr="Développement",
                skill_type=SkillType.HARD,
                status=TaxonomyStatus.VALIDATED,
            )
        )
        db.commit()

    skills = client.get("/api/v1/employer/catalogs/skills?q=développement&limit=5")
    languages = client.get("/api/v1/employer/catalogs/languages")
    assert skills.status_code == 200
    assert skills.json() == [{"skill_code": "SK-CATALOG", "label": "Développement"}]
    assert languages.status_code == 200
    assert [item["level"] for item in languages.json()["levels"]] == [1, 2, 3, 4]
    assert {"code": "ar-TN", "label": "Arabic (Tunisia)"} in languages.json()["languages"]


def test_candidate_application_list_is_scoped_to_own_profile(application_client):
    client, _sessions, active_user, _employer, _candidate_id, _employer_id, _other_id, offer_id = application_client
    client.post("/api/v1/me/applications", json={"job_offer_id": str(offer_id), "employer_contact_consent": True})
    active_user["value"] = type("UserRef", (), {"id": uuid.uuid4()})()

    assert client.get("/api/v1/me/applications").status_code == 404


def test_candidate_cannot_apply_to_expired_published_offer(application_client):
    client, sessions, _user, _employer, _candidate_id, _employer_id, _other_id, offer_id = application_client
    with sessions() as db:
        db.get(JobOffer, offer_id).expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    response = client.post(
        "/api/v1/me/applications",
        json={"job_offer_id": str(offer_id), "employer_contact_consent": True},
    )
    assert response.status_code == 404
