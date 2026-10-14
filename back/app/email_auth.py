"""One-time email verification and password reset flows."""

from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
import hashlib
import logging
import secrets
import smtplib
import ssl
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .database import get_db
from .models import AccountActionToken, AuthIdentity, AuthProvider, Employer, User, normalize_email
from .security import hash_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/email", tags=["email authentication"])
VERIFY = "email_verification"
RESET = "password_reset"
VERIFY_LIFETIME = timedelta(hours=24)
RESET_LIFETIME = timedelta(minutes=30)
RESEND_COOLDOWN = timedelta(seconds=60)


class EmailRequest(BaseModel):
    email: EmailStr


class TokenRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class PasswordResetRequest(TokenRequest):
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not any(char.islower() for char in value) or not any(char.isupper() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("Password must include lowercase, uppercase, and numeric characters")
        return value


class EmailActionResponse(BaseModel):
    message: str
    delivery_configured: bool


def _mail_configured(settings: Settings) -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


def _send_email(settings: Settings, recipient: str, subject: str, body: str) -> bool:
    if not _mail_configured(settings):
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = recipient
    message.set_content(body)
    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10, context=ssl.create_default_context()) as client:
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password or "")
                client.send_message(message)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
                client.ehlo()
                if settings.smtp_starttls:
                    client.starttls(context=ssl.create_default_context())
                    client.ehlo()
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password or "")
                client.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        logger.warning("Unable to send account security email")
        return False


def _issue_token(db: Session, user: User, purpose: str, settings: Settings) -> bool:
    if not _mail_configured(settings):
        return False

    now = datetime.now(UTC)
    db.execute(delete(AccountActionToken).where(AccountActionToken.expires_at < now - timedelta(days=30)))
    latest = db.scalar(
        select(AccountActionToken)
        .where(AccountActionToken.user_id == user.id, AccountActionToken.purpose == purpose)
        .order_by(AccountActionToken.created_at.desc())
        .limit(1)
    )
    if latest is not None:
        created_at = latest.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if now - created_at < RESEND_COOLDOWN:
            return False

    db.query(AccountActionToken).filter(
        AccountActionToken.user_id == user.id,
        AccountActionToken.purpose == purpose,
        AccountActionToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)

    raw_token = secrets.token_urlsafe(32)
    lifetime = VERIFY_LIFETIME if purpose == VERIFY else RESET_LIFETIME
    record = AccountActionToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        purpose=purpose,
        expires_at=now + lifetime,
    )
    db.add(record)
    db.commit()

    page = "verify-email" if purpose == VERIFY else "reset-password"
    link = f"{settings.frontend_url.rstrip('/')}/{page}?token={raw_token}"
    if purpose == VERIFY:
        subject = "Vérifiez votre adresse e-mail — Mahara Match"
        body = f"Bonjour,\n\nPour vérifier votre adresse e-mail, ouvrez ce lien :\n{link}\n\nCe lien expire dans 24 heures. Si vous n’avez pas créé de compte Mahara Match, ignorez ce message."
    else:
        subject = "Réinitialisez votre mot de passe — Mahara Match"
        body = f"Bonjour,\n\nPour choisir un nouveau mot de passe, ouvrez ce lien :\n{link}\n\nCe lien expire dans 30 minutes. Si vous n’avez pas demandé cette réinitialisation, ignorez ce message."

    sent = _send_email(settings, user.email or "", subject, body)
    if not sent:
        record.used_at = now
        db.commit()
    return sent


def _user_for_token(db: Session, raw_token: str, purpose: str) -> tuple[AccountActionToken, User]:
    digest = hashlib.sha256(raw_token.encode()).hexdigest()
    record = db.scalar(
        select(AccountActionToken)
        .where(AccountActionToken.token_hash == digest, AccountActionToken.purpose == purpose)
        .with_for_update()
    )
    now = datetime.now(UTC)
    if record is None or record.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This link is invalid or has already been used")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This link has expired. Request a new one.")
    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This link is invalid")
    record.used_at = now
    return record, user


@router.post("/verification/request", response_model=EmailActionResponse, status_code=status.HTTP_202_ACCEPTED)
def request_verification(payload: EmailRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> EmailActionResponse:
    email = normalize_email(str(payload.email))
    user = db.scalar(select(User).where(User.email == email))
    if user is not None and not user.email_verified:
        _issue_token(db, user, VERIFY, settings)
    return EmailActionResponse(
        message="If this address belongs to an unverified account, a verification link will be sent.",
        delivery_configured=_mail_configured(settings),
    )


@router.post("/verification/confirm")
def confirm_verification(payload: TokenRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    _, user = _user_for_token(db, payload.token, VERIFY)
    user.email_verified = True
    db.query(AuthIdentity).filter(AuthIdentity.user_id == user.id).update({"email_verified": True})
    db.commit()
    return {"message": "Your email address has been verified."}


@router.post("/password-reset/request", response_model=EmailActionResponse, status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: EmailRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> EmailActionResponse:
    email = normalize_email(str(payload.email))
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        identity = db.scalar(
            select(AuthIdentity).where(AuthIdentity.user_id == user.id, AuthIdentity.provider == AuthProvider.PASSWORD)
        )
        if identity is not None and identity.password_hash:
            _issue_token(db, user, RESET, settings)
    return EmailActionResponse(
        message="If this address belongs to an account with a password, a reset link will be sent.",
        delivery_configured=_mail_configured(settings),
    )


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    _, user = _user_for_token(db, payload.token, RESET)
    identity = db.scalar(
        select(AuthIdentity).where(AuthIdentity.user_id == user.id, AuthIdentity.provider == AuthProvider.PASSWORD)
    )
    if identity is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account cannot use password sign-in")
    password_hash = hash_password(payload.new_password)
    identity.password_hash = password_hash
    db.query(Employer).filter(Employer.user_id == user.id).update({"password_hash": password_hash})
    db.commit()
    return {"message": "Your password has been reset. You can now sign in."}
