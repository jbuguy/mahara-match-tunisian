"""Verify Mahara-issued access tokens and load the corresponding Postgres user."""

from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import User
from app.services.users import get_or_create_user

AUDIENCE = "mahara-match-wp6"
ISSUER = "mahara-match"
ALGORITHMS = ["HS256"]

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user: User
    name: str | None


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    if not settings.jwt_secret or len(settings.jwt_secret.encode("utf-8")) < 32:
        raise HTTPException(status_code=503, detail="authentication is not configured")
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "sub", "email"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise unauthorized("token expired") from exc
    except jwt.PyJWTError as exc:
        raise unauthorized("invalid token") from exc


def display_name(claims: dict[str, Any]) -> str | None:
    return claims.get("name") or None


def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """FastAPI dependency: a valid Mahara access token, without touching the database."""
    if credentials is None:
        raise unauthorized("missing token")
    return decode_token(credentials.credentials, settings)


def get_current_user(
    claims: dict[str, Any] = Depends(get_token_claims),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """FastAPI dependency for every signed-in endpoint that needs our `users` row."""
    email = str(claims["email"]).strip().lower()
    if not email:
        raise unauthorized("token has no email")
    return CurrentUser(user=get_or_create_user(db, email), name=display_name(claims))
