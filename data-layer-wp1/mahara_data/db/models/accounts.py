from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ... import enums as e
from .. import enum_types as t
from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin


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
