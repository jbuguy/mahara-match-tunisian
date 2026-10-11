"""Shared lookups for canonical platform accounts and domain records."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from mahara_data.db.models.accounts import User
from mahara_data.db.models.candidates import Candidate
from mahara_data.db.models.employers import Employer


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def get_candidate_for_user(db: Session, user_id: UUID) -> Candidate | None:
    return db.scalar(select(Candidate).where(Candidate.user_id == user_id))


def get_employer_for_user(db: Session, user_id: UUID) -> Employer | None:
    return db.scalar(select(Employer).where(Employer.user_id == user_id))