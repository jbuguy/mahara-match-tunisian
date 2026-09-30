"""Supabase login tokens: verify the ES256 signature against the project's JWKS, then load our `users` row."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import User
from app.services.users import get_or_create_user

AUDIENCE = "authenticated"
ALGORITHMS = ["ES256"]  # Supabase asymmetric signing keys; the old HS256 secret is never accepted.

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user: User
    name: str | None


def supabase_auth_url(settings: Settings) -> str:
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is not set in employee-module-wp6/.env")
    return f"{settings.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def get_jwks_client() -> PyJWKClient:
    """FastAPI dependency: one cached JWKS client per process (keys are cached too)."""
    return PyJWKClient(f"{supabase_auth_url(get_settings())}/.well-known/jwks.json", cache_keys=True)


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_token(token: str, jwks: PyJWKClient, settings: Settings) -> dict[str, Any]:
    try:
        signing_key = jwks.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key,
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
            issuer=supabase_auth_url(settings),
            options={"require": ["exp", "sub", "email"]},
        )
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(status_code=503, detail="auth keys unavailable") from exc
    except jwt.ExpiredSignatureError as exc:
        raise unauthorized("token expired") from exc
    except jwt.PyJWTError as exc:
        raise unauthorized("invalid token") from exc


def display_name(claims: dict[str, Any]) -> str | None:
    metadata = claims.get("user_metadata") or {}
    return metadata.get("full_name") or metadata.get("name") or None


def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    jwks: PyJWKClient = Depends(get_jwks_client),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """FastAPI dependency: a valid login token, without touching the database (used by /reference/*)."""
    if credentials is None:
        raise unauthorized("missing token")
    return decode_token(credentials.credentials, jwks, settings)


def get_current_user(
    claims: dict[str, Any] = Depends(get_token_claims),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """FastAPI dependency for every signed-in endpoint that needs our `users` row."""
    email = str(claims["email"]).strip().lower()
    if not email:
        raise unauthorized("token has no email")
    return CurrentUser(user=get_or_create_user(db, email), name=display_name(claims))
