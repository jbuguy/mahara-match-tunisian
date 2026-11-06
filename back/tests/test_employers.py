import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app, asgi_app
from app.models import AuthIdentity, Employer, User
from app.security import create_user_access_token, ensure_employer_email_verified


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

valid_payload = {
    "company_name": "Carthage Digital",
    "email": "hr@carthage.tn",
    "password": "StrongPass123!",
    "sector": "Technology",
    "company_size": "11-50",
}


def setup_function():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


def test_signup_returns_profile_without_password_hash():
    response = client.post("/employers/signup", json=valid_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == valid_payload["email"]
    assert body["verified"] is False
    assert "password_hash" not in body


def test_development_signup_skips_employer_email_verification():
    response = client.post("/employers/signup", json=valid_payload)

    assert response.status_code == 201
    assert response.json()["email_verified"] is True
    with TestSession() as db:
        user = db.query(User).filter_by(email=valid_payload["email"]).one()
        identity = db.query(AuthIdentity).filter_by(user_id=user.id).one()
        employer = db.query(Employer).filter_by(email=valid_payload["email"]).one()

        assert user.email_verified is True
        assert identity.email_verified is True
        assert ensure_employer_email_verified(db, employer) is employer


def test_production_signup_still_requires_employer_email_verification(monkeypatch):
    monkeypatch.setattr("app.main.settings.app_env", "production")

    response = client.post("/employers/signup", json=valid_payload)

    assert response.status_code == 201
    assert response.json()["email_verified"] is False
    with TestSession() as db:
        user = db.query(User).filter_by(email=valid_payload["email"]).one()
        employer = db.query(Employer).filter_by(email=valid_payload["email"]).one()

        assert user.email_verified is False
        with pytest.raises(HTTPException) as exc_info:
            ensure_employer_email_verified(db, employer)

    assert exc_info.value.status_code == 403


def test_development_candidate_signup_skips_email_verification():
    response = client.post(
        "/candidates/signup",
        json={
            "full_name": "Candidate Test",
            "email": "candidate@example.com",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == 201
    assert response.json()["email_verified"] is True
    with TestSession() as db:
        user = db.query(User).filter_by(email="candidate@example.com").one()
        identity = db.query(AuthIdentity).filter_by(user_id=user.id).one()
        assert user.email_verified is True
        assert identity.email_verified is True


def test_production_candidate_signup_still_requires_email_verification(monkeypatch):
    monkeypatch.setattr("app.main.settings.app_env", "production")

    response = client.post(
        "/candidates/signup",
        json={
            "full_name": "Candidate Test",
            "email": "candidate@example.com",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == 201
    assert response.json()["email_verified"] is False
    with TestSession() as db:
        user = db.query(User).filter_by(email="candidate@example.com").one()
        identity = db.query(AuthIdentity).filter_by(user_id=user.id).one()
        assert user.email_verified is False
        assert identity.email_verified is False


def test_duplicate_email_is_rejected():
    client.post("/employers/signup", json=valid_payload)

    response = client.post("/employers/signup", json=valid_payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "An employer with this email already exists"


def test_login_returns_jwt_and_profile_is_protected():
    client.post("/employers/signup", json=valid_payload)
    login = client.post(
        "/employers/login",
        json={"email": valid_payload["email"], "password": valid_payload["password"]},
    )

    assert login.status_code == 200
    token = login.json()["access_token"]
    profile = client.get("/employers/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["company_name"] == valid_payload["company_name"]


def test_login_rejects_wrong_password_and_profile_rejects_invalid_token():
    client.post("/employers/signup", json=valid_payload)

    wrong_password = client.post(
        "/employers/login",
        json={"email": valid_payload["email"], "password": "WrongPass123!"},
    )
    missing_token = client.get("/employers/me")
    invalid_token = client.get("/employers/me", headers={"Authorization": "Bearer invalid"})

    assert wrong_password.status_code == 401
    assert missing_token.status_code == 401
    assert invalid_token.status_code == 401


def test_signup_rejects_weak_password_and_missing_fields():
    weak_password = {**valid_payload, "password": "short"}
    simple_password = {**valid_payload, "password": "password"}
    missing_sector = {key: value for key, value in valid_payload.items() if key != "sector"}

    assert client.post("/employers/signup", json=weak_password).status_code == 422
    assert client.post("/employers/signup", json=simple_password).status_code == 422
    assert client.post("/employers/signup", json=missing_sector).status_code == 422


def test_profile_can_be_updated():
    signup = client.post("/employers/signup", json=valid_payload)
    employer_id = signup.json()["id"]
    token = client.post(
        "/employers/login",
        json={"email": valid_payload["email"], "password": valid_payload["password"]},
    ).json()["access_token"]

    response = client.patch(
        "/employers/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "Updated Carthage", "company_size": "51-200"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == employer_id
    assert response.json()["company_name"] == "Updated Carthage"
    assert response.json()["company_size"] == "51-200"


def test_platform_health_and_readiness_endpoints_are_available():
    health = client.get("/health")
    readiness = client.get("/ready")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["service"] == "mahara-match"

    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ready"
    assert readiness.json()["checks"]["database"] == "ok"
    assert readiness.json()["checks"]["shared_contracts"] == "ok"


def test_development_cors_allows_vite_fallback_port():
    response = TestClient(asgi_app).options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"


def test_platform_module_registry_lists_integrated_features():
    response = client.get("/platform/modules")

    assert response.status_code == 200
    payload = response.json()
    assert payload["platform"] == "mahara-match"
    assert any(module["code"] == "data" for module in payload["modules"])
    assert any(module["code"] == "employer" for module in payload["modules"])
    assert any(module["code"] == "matching" for module in payload["modules"])
    assert all(module["shared_contracts"] in {"ok", "not_configured"} for module in payload["modules"])


def test_platform_contracts_endpoint_exposes_shared_schema_catalog():
    response = client.get("/platform/contracts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "shared"
    assert "candidate_profile" in payload["contracts"]
    assert "job_offer" in payload["contracts"]
    assert "application" in payload["contracts"]


def test_platform_modules_expose_module_status_and_contract_counts():
    response = client.get("/platform/modules")

    assert response.status_code == 200
    modules = response.json()["modules"]
    data_module = next(module for module in modules if module["code"] == "data")
    assert data_module["status"] == "registered"
    assert data_module["contract_count"] >= 10
    assert "candidate_profile" in data_module["contracts"]
    assert any(module["code"] == "employer" for module in modules)
    assert any(module["code"] == "employee" for module in modules)
    matching_module = next(module for module in modules if module["code"] == "matching")
    assert matching_module["status"] == "registered"


def test_disabling_user_revokes_existing_access_and_prevents_login():
    response = client.post("/employers/signup", json=valid_payload)
    assert response.status_code == 201
    token = client.post(
        "/employers/login",
        json={"email": valid_payload["email"], "password": valid_payload["password"]},
    ).json()["access_token"]

    with TestSession() as db:
        user = db.query(User).filter_by(email=valid_payload["email"]).one()
        user.is_active = False
        db.commit()

    profile = client.get("/employers/me", headers={"Authorization": f"Bearer {token}"})
    login = client.post(
        "/employers/login",
        json={"email": valid_payload["email"], "password": valid_payload["password"]},
    )

    assert profile.status_code == 401
    assert login.status_code == 401


def test_disabling_candidate_revokes_existing_user_token():
    with TestSession() as db:
        user = User(email="inactive@example.com", roles=["candidate"])
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_user_access_token(user)
        user.is_active = False
        db.commit()

    response = client.get(
        "/api/v1/me/roles",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_login_rate_limit_is_configurable_and_returns_retry_after(monkeypatch):
    monkeypatch.setattr("app.main.settings.auth_login_rate_limit", 2)

    attempts = [
        client.post(
            "/employers/login",
            json={"email": "unknown@example.com", "password": "WrongPassword123!"},
        )
        for _ in range(3)
    ]

    assert [response.status_code for response in attempts] == [401, 401, 429]
    assert int(attempts[2].headers["retry-after"]) > 0


def test_google_sign_in_start_uses_login_rate_limit(monkeypatch):
    monkeypatch.setattr("app.main.settings.auth_login_rate_limit", 1)

    first = client.get("/auth/google")
    second = client.get("/auth/google")

    assert first.status_code == 503
    assert second.status_code == 429


def test_signup_rate_limit_is_configurable(monkeypatch):
    monkeypatch.setattr("app.main.settings.auth_signup_rate_limit", 1)

    first = client.post("/employers/signup", json=valid_payload)
    second = client.post("/employers/signup", json=valid_payload)

    assert first.status_code == 201
    assert second.status_code == 429


def test_email_verification_and_password_reset_routes_are_rate_limited(monkeypatch):
    monkeypatch.setattr("app.main.settings.auth_email_rate_limit", 1)
    email_payload = {"email": "unknown@example.com"}

    for path in ("/auth/email/verification/request", "/auth/email/password-reset/request"):
        assert client.post(path, json=email_payload).status_code == 202
        assert client.post(path, json=email_payload).status_code == 429

    verify_payload = {"token": "not-a-valid-verification-token"}
    reset_payload = {
        "token": "not-a-valid-password-reset-token",
        "new_password": "StrongPassword123!",
    }
    assert client.post("/auth/email/verification/confirm", json=verify_payload).status_code == 400
    assert client.post("/auth/email/verification/confirm", json=verify_payload).status_code == 429
    assert client.post("/auth/email/password-reset/confirm", json=reset_payload).status_code == 400
    assert client.post("/auth/email/password-reset/confirm", json=reset_payload).status_code == 429


def test_platform_validates_employer_offers_and_candidate_profiles():
    offer_response = client.post(
        "/platform/contracts/job-offer/validate",
        json={
            "title": "Full Stack Developer",
            "description": "Build and maintain the platform backend and integrations for Tunisian employers.",
            "contract_type": "cdi",
            "location": {"governorate_code": "TN-11", "delegation": "Tunis"},
            "positions_count": 1,
            "skills": [{"skill_code": "SK-0103", "requirement": "required", "min_level": 2}],
            "employer_id": "123e4567-e89b-12d3-a456-426614174000",
            "occupation_code": "OC-2512",
            "status": "draft",
            "source": "employer_form",
        },
    )
    profile_response = client.post(
        "/platform/contracts/candidate-profile/validate",
        json={
            "onboarding_path": "cv_upload",
            "literacy_level": "literate",
            "preferred_language": "fr",
            "languages": [{"code": "fr", "level": 2}],
            "location": {"governorate_code": "TN-11", "delegation": "Tunis"},
            "education_level": "licence",
            "years_experience": 3,
            "skills": [{"skill_code": "SK-0103", "skill_type": "hard", "level": 3, "source": "cv", "confidence": 0.95}],
            "source_document_ids": ["123e4567-e89b-12d3-a456-426614174001"],
            "experiences": [{"job_title_raw": "Developer", "occupation_code": "OC-2512", "is_informal": False, "duration_months": 24, "governorate_code": "TN-11"}],
            "summary": "Product and platform developer with backend and frontend experience.",
        },
    )

    assert offer_response.status_code == 200
    assert offer_response.json()["valid"] is True
    assert offer_response.json()["contract"] == "job_offer"

    assert profile_response.status_code == 200
    assert profile_response.json()["valid"] is True
    assert profile_response.json()["contract"] == "candidate_profile"


def test_platform_validates_onboarding_output_against_shared_contracts():
    response = client.post(
        "/platform/contracts/onboarding/validate",
        json={
            "onboarding_path": "derja_guided_voice",
            "literacy_level": "non_literate",
            "preferred_language": "ar-TN",
            "languages": [{"code": "ar-TN", "level": 2}],
            "location": {"governorate_code": "TN-11", "delegation": "Tunis"},
            "education_level": "baccalaureate",
            "years_experience": 2,
            "skills": [{"skill_code": "SK-0103", "skill_type": "hard", "level": 2, "source": "dialogue", "confidence": 0.8}],
            "conversation_session_id": "123e4567-e89b-12d3-a456-426614174002",
            "summary": "Candidate with a short professional history and onboarding through guided Derja voice flow.",
        },
    )

    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["contract"] == "candidate_profile"
    assert response.json()["module"] == "onboarding"
