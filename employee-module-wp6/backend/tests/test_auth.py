from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import jwt

from app.config import Settings, get_settings
from app.db import get_db
from app.main import app
from app.routers import auth as auth_router

JWT_SECRET = "test-secret-that-is-at-least-32-bytes"


class FakeTokenResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"id_token": "google-id-token"}


class FakeGoogleClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        pass

    async def post(self, url, data):
        assert url == auth_router.GOOGLE_TOKEN_URL
        assert data["grant_type"] == "authorization_code"
        assert data["code_verifier"]
        return FakeTokenResponse()


def test_google_oauth_callback_issues_maharatoken(client, monkeypatch):
    settings = Settings(
        _env_file=None,
        google_client_id="google-client-id",
        google_client_secret="google-client-secret",
        jwt_secret=JWT_SECRET,
        api_base_url="http://testserver",
        frontend_url="http://localhost:5173",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(auth_router.httpx, "AsyncClient", lambda **_kwargs: FakeGoogleClient())
    monkeypatch.setattr(
        auth_router,
        "_decode_google_id_token",
        lambda *_args: {
            "sub": "google-subject",
            "email": "Candidate@Example.tn",
            "email_verified": True,
            "name": "Candidate Name",
            "picture": "https://example.tn/photo.jpg",
        },
    )
    user = SimpleNamespace(id="c45c35d3-73c1-4497-8a19-4f39f2f68734", email="candidate@example.tn")
    looked_up = {}

    def get_user(_db, email):
        looked_up["email"] = email
        return user

    monkeypatch.setattr(auth_router, "get_or_create_user", get_user)

    start = client.get("/api/v1/auth/google", follow_redirects=False)
    authorization = urlparse(start.headers["location"])
    query = parse_qs(authorization.query)
    state = query["state"][0]
    assert query["code_challenge_method"] == ["S256"]
    assert start.cookies[auth_router.STATE_COOKIE] == state
    assert auth_router.VERIFIER_COOKIE in start.cookies

    callback = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "one-time-code", "state": state},
        follow_redirects=False,
    )

    assert callback.status_code == 303
    assert callback.headers["location"].startswith("http://localhost:5173/auth/callback#access_token=")
    assert callback.headers["cache-control"] == "no-store"
    assert callback.headers["referrer-policy"] == "no-referrer"
    assert looked_up["email"] == "candidate@example.tn"
    token = callback.headers["location"].split("access_token=", maxsplit=1)[1]
    claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience="mahara-match-wp6", issuer="mahara-match")
    assert claims["sub"] == user.id
    assert claims["name"] == "Candidate Name"
    assert claims["picture"] == "https://example.tn/photo.jpg"
    assert callback.headers.get_list("set-cookie")


def test_google_oauth_callback_rejects_state_mismatch(client):
    app.dependency_overrides[get_db] = lambda: object()
    response = client.get(
        "/api/v1/auth/google/callback?code=one-time-code&state=wrong",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=oauth_state_invalid" in response.headers["location"]