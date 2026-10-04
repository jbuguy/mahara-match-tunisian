from fastapi.testclient import TestClient

from app.config import get_settings
from app.google_auth import _issue_access_token
from app.main import app
from mahara_wp6.auth import decode_token
from mahara_wp6.config import Settings as WP6Settings

client = TestClient(app)


def test_google_oauth_endpoint_exists_and_requires_configuration():
    response = client.get("/auth/google")

    assert response.status_code == 503
    assert "Google authentication is not configured" in response.json()["detail"]


def test_root_api_exposes_wp4_and_wp6_routes():
    paths = app.openapi()["paths"]

    assert "/employer-agent/sessions" in paths
    assert "/api/v1/me" in paths
    assert "/api/v1/me/profile" in paths
    assert "/api/v1/reference/governorates" in paths
    assert "/api/v1/me/cv" in paths
    assert "/api/v1/me/photo" in paths
    assert "/api/v1/me/assistant/chat" in paths


def test_google_access_token_matches_wp6_auth_contract():
    settings = get_settings()
    token = _issue_access_token("candidate@example.com", "Candidate", None, settings)
    claims = decode_token(token, WP6Settings(jwt_secret=settings.jwt_secret))

    assert claims["sub"] == "candidate@example.com"
    assert claims["email"] == "candidate@example.com"
