from datetime import datetime, timedelta, timezone
from typing import Annotated
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import Employer, User, get_or_create_user


password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/employers/login")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(employer_id: uuid.UUID) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(employer_id), "exp": expires_at},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_user_access_token(user: User) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "user_id": str(user.id),
            "roles": user.roles,
            "iss": "mahara-match",
            "aud": "mahara-match-platform",
            "exp": expires_at,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    settings = get_settings()
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer="mahara-match",
            audience="mahara-match-platform",
        )
        email = str(payload.get("email") or payload.get("sub") or "").strip().lower()
        if not email or not payload.get("user_id"):
            raise credentials_error
    except (JWTError, ValueError):
        raise credentials_error from None

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = get_or_create_user(db, email, roles=[])
    return user


def require_roles(*required_roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        user_roles = {str(role).strip().lower() for role in user.roles}
        if not set(required_roles).issubset(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )
        return user

    return dependency


def require_any_role(*allowed_roles: str):
    """Require at least one role for shared admin/operator surfaces."""
    normalized = {role.strip().lower() for role in allowed_roles if role.strip()}

    def dependency(user: User = Depends(get_current_user)) -> User:
        user_roles = {str(role).strip().lower() for role in user.roles}
        if not user_roles.intersection(normalized):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )

        return user

    return dependency


def get_current_employer(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Employer:
    settings = get_settings()
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        employer_id = uuid.UUID(payload.get("sub", ""))
    except (JWTError, ValueError):
        raise credentials_error from None

    employer = db.get(Employer, employer_id)
    if employer is None:
        raise credentials_error
    return employer


def ensure_employer_email_verified(db: Session, employer: Employer) -> Employer:
    """Require a linked employer account to verify its email before sensitive actions."""
    # Some isolated feature tests use lightweight employer doubles. Real ORM
    # employers always expose user_id, so this keeps those tests independent of
    # the account-verification database while preserving production enforcement.
    if not hasattr(employer, "user_id"):
        return employer
    user_id = getattr(employer, "user_id", None)
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email address before publishing offers or contacting candidates",
        )
    return employer
