import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from jwt import PyJWKClient

from .config import Settings, get_settings
from .database import get_db
from .models import AuthIdentity, AuthProvider, User, get_or_create_user

ISSUER = "mahara-match"
AUDIENCE = "mahara-match-wp6"
router = APIRouter(prefix="/auth", tags=["auth"])
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
STATE_COOKIE = "mahara_oauth_state"
VERIFIER_COOKIE = "mahara_oauth_verifier"
COOKIE_PATH = "/auth/google"
TOKEN_LIFETIME = timedelta(minutes=60)


@lru_cache
def get_google_jwks_client() -> PyJWKClient:
    return PyJWKClient(GOOGLE_JWKS_URL, cache_keys=True)


def _callback_uri(settings: Settings) -> str:
    return f"{settings.api_base_url.rstrip('/')}/auth/google/callback"


def _secure_cookie(settings: Settings) -> bool:
    return settings.app_env.lower() not in {"dev", "development", "test"}


def _clear_oauth_cookies(response: RedirectResponse, settings: Settings) -> None:
    for name in (STATE_COOKIE, VERIFIER_COOKIE):
        response.delete_cookie(name, path=COOKIE_PATH, secure=_secure_cookie(settings), httponly=True, samesite="lax")


def _decode_google_id_token(token: str, jwks: PyJWKClient, settings: Settings) -> dict:
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google authentication is not configured")
    try:
        claims = jwt.decode(
            token,
            jwks.get_signing_key_from_jwt(token),
            algorithms=["RS256"],
            audience=settings.google_client_id,
            options={"require": ["exp", "sub", "email", "iss"]},
        )
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(status_code=503, detail="Google authentication keys unavailable") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid Google identity token") from exc

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise HTTPException(status_code=401, detail="Invalid Google identity token")
    if claims.get("email_verified") not in (True, "true"):
        raise HTTPException(status_code=403, detail="Google email is not verified")
    return claims


def _issue_access_token(email: str, name: str | None, picture: str | None, settings: Settings) -> str:
    if not settings.jwt_secret or len(settings.jwt_secret.encode("utf-8")) < 32:
        raise HTTPException(status_code=503, detail="Google authentication is not configured")
    now = datetime.now(UTC)
    claims = {
        "sub": email,
        "email": email,
        "name": name or email,
        "picture": picture,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.get("/google")
def start_google_sign_in(settings: Settings = Depends(get_settings)) -> RedirectResponse:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google authentication is not configured")

    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")

    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": _callback_uri(settings),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    response = RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}", status_code=302)
    for name, value in ((STATE_COOKIE, state), (VERIFIER_COOKIE, verifier)):
        response.set_cookie(
            name,
            value,
            max_age=300,
            httponly=True,
            secure=_secure_cookie(settings),
            samesite="lax",
            path=COOKIE_PATH,
        )
    return response


@router.get("/google/callback")
async def finish_google_sign_in(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    settings: Settings = Depends(get_settings),
    db=Depends(get_db),
    jwks: PyJWKClient = Depends(get_google_jwks_client),
) -> RedirectResponse:
    if error:
        response = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/auth/callback?error={error}", status_code=303)
        _clear_oauth_cookies(response, settings)
        return response

    expected_state = request.cookies.get(STATE_COOKIE)
    verifier = request.cookies.get(VERIFIER_COOKIE)
    if not code or not state or not expected_state or not secrets.compare_digest(state, expected_state) or not verifier:
        response = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/auth/callback?error=oauth_state_invalid", status_code=303)
        _clear_oauth_cookies(response, settings)
        return response
    if not settings.google_client_id or not settings.google_client_secret:
        response = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/auth/callback?error=google_auth_not_configured", status_code=303)
        _clear_oauth_cookies(response, settings)
        return response

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": _callback_uri(settings),
                    "grant_type": "authorization_code",
                    "code_verifier": verifier,
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
    except (httpx.HTTPError, ValueError):
        response = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/auth/callback?error=google_token_exchange_failed", status_code=303)
        _clear_oauth_cookies(response, settings)
        return response

    identity_token = token_data.get("id_token")
    if not isinstance(identity_token, str):
        response = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/auth/callback?error=google_identity_missing", status_code=303)
        _clear_oauth_cookies(response, settings)
        return response

    try:
        google_claims = _decode_google_id_token(identity_token, jwks, settings)
    except HTTPException as exc:
        response = RedirectResponse(
            f"{settings.frontend_url.rstrip('/')}/auth/callback?error={exc.detail if isinstance(exc.detail, str) else 'google_identity_invalid'}",
            status_code=303,
        )
        _clear_oauth_cookies(response, settings)
        return response

    email = str(google_claims.get("email", "")).strip().lower()
    if not email:
        response = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/auth/callback?error=google_email_missing", status_code=303)
        _clear_oauth_cookies(response, settings)
        return response

    user = get_or_create_user(db, email, roles=["candidate"], email_verified=True)
    AuthIdentity.link_user(
        db,
        user,
        provider=AuthProvider.GOOGLE,
        provider_user_id=str(google_claims.get("sub", "")),
        email=email,
        email_verified=True,
    )
    db.commit()

    access_token = _issue_access_token(email, google_claims.get("name"), google_claims.get("picture"), settings)
    response = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/auth/callback#access_token={access_token}", status_code=303)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    _clear_oauth_cookies(response, settings)
    return response