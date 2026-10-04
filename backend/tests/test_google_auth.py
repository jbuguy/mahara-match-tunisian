from sqlalchemy import create_engine
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base
from app.google_auth import _issue_access_token
from app.main import app
from app.models import AuthIdentity, AuthProvider, Candidate, User, ensure_user_has_role, get_or_create_candidate_for_user, get_or_create_user
from mahara_wp6.auth import decode_token
from mahara_wp6.config import Settings as WP6Settings

client = TestClient(app)
test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=test_engine)


def setup_function():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


def test_google_oauth_endpoint_exists_and_requires_configuration():
    response = client.get("/auth/google")

    assert response.status_code == 503
    assert "Google authentication is not configured" in response.json()["detail"]


def test_root_api_exposes_wp4_and_wp6_routes():
    paths = app.openapi()["paths"]

    assert "/employer-agent/sessions" in paths
    assert "/api/v1/me" in paths
    assert "/api/v1/me/profile" in paths
    assert "/api/v1/onboarding/sessions" in paths
    assert "/api/v1/reference/governorates" in paths
    assert "/api/v1/me/cv" in paths
    assert "/api/v1/me/photo" in paths
    assert "/api/v1/me/assistant/chat" in paths
    assert "/api/v1/me/applications" in paths
    assert "/api/v1/employer/applications" in paths


def test_google_access_token_matches_wp6_auth_contract():
    settings = get_settings()
    token = _issue_access_token("candidate@example.com", "Candidate", None, settings)
    claims = decode_token(token, WP6Settings(jwt_secret=settings.jwt_secret))

    assert claims["sub"] == "candidate@example.com"
    assert claims["email"] == "candidate@example.com"


def test_canonical_identity_layer_supports_shared_user_and_google_link():
    with TestSession() as db:
        user = get_or_create_user(
            db,
            "Candidate@Example.com",
            roles=["candidate"],
            email_verified=True,
        )

        assert user.email == "candidate@example.com"
        assert user.email_verified is True
        assert "candidate" in user.roles

        ensure_user_has_role(user, "employer")
        assert {"candidate", "employer"} <= set(user.roles)

        identity = AuthIdentity.link_user(
            db,
            user,
            provider=AuthProvider.GOOGLE,
            provider_user_id="google-123",
            email="candidate@example.com",
            email_verified=True,
        )

        assert identity.provider is AuthProvider.GOOGLE
        assert identity.user_id == user.id
        assert db.query(AuthIdentity).count() == 1

        candidate = get_or_create_candidate_for_user(db, user, onboarding_path="cv_upload")
        assert candidate.user_id == user.id
        assert db.query(Candidate).count() == 1
