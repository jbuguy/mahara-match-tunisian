from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app


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
    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"


def test_platform_module_registry_lists_work_packages_with_shared_contracts():
    response = client.get("/platform/modules")

    assert response.status_code == 200
    payload = response.json()
    assert payload["platform"] == "mahara-match"
    assert any(module["code"] == "wp1" for module in payload["modules"])
    assert any(module["code"] == "wp4" for module in payload["modules"])
    assert any(module["code"] == "wp3" for module in payload["modules"])
    assert all(module["shared_contracts"] in {"ok", "not_configured"} for module in payload["modules"])


def test_platform_contracts_endpoint_exposes_wp1_schema_catalog():
    response = client.get("/platform/contracts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "wp1"
    assert "candidate_profile" in payload["contracts"]
    assert "job_offer" in payload["contracts"]
    assert "application" in payload["contracts"]


def test_platform_modules_expose_module_status_and_contract_counts():
    response = client.get("/platform/modules")

    assert response.status_code == 200
    modules = response.json()["modules"]
    wp1 = next(module for module in modules if module["code"] == "wp1")
    assert wp1["status"] == "registered"
    assert wp1["contract_count"] >= 10
    assert "candidate_profile" in wp1["contracts"]
    assert any(module["code"] == "wp4" for module in modules)
    wp3 = next(module for module in modules if module["code"] == "wp3")
    assert wp3["status"] == "registered"
    assert any(module["code"] == "wp6" for module in modules)


def test_platform_validates_wp4_offers_and_wp6_profiles_against_wp1_contracts():
    offer_response = client.post(
        "/platform/integrations/wp4/validate-offer",
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
        "/platform/integrations/wp6/validate-profile",
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


def test_platform_validates_onboarding_agent_output_against_wp1_contracts():
    response = client.post(
        "/platform/integrations/wp2/onboard",
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
    assert response.json()["module"] == "wp2"