import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ... import enums as e
from .. import enum_types as t
from ..base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Platform account; `role` drives RBAC (see WP5)."""

    __tablename__ = "users"
    # Non-literate candidates may only have a phone number.
    __table_args__ = (CheckConstraint("email is not null or phone is not null", name="users_contact_required"),)

    role: Mapped[e.UserRole] = mapped_column(t.user_role, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)  # E.164, e.g. +21620123456
    password_hash: Mapped[str | None] = mapped_column(String(255))  # null for OTP-only accounts
    preferred_language: Mapped[str] = mapped_column(String(8), default="ar-TN", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    roles: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)


class AuthIdentity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """External or password identity linked to one canonical platform user."""

    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_auth_identity_user_provider"),
        UniqueConstraint("provider", "provider_user_id", name="uq_auth_identity_provider_subject"),
        CheckConstraint("provider in ('google', 'password')", name="auth_identities_provider_check"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
