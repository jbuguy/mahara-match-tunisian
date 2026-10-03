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