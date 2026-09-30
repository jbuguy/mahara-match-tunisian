import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Candidate, User


# last_login_at is refreshed at most this often: writing it on every request cost two database round trips.
LAST_LOGIN_EVERY = timedelta(minutes=15)


def get_or_create_user(db: Session, email: str) -> User:
    """Find the `users` row for a (lower-cased) email, create it on first login, stamp last_login_at."""
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(id=uuid.uuid4(), email=email, role="candidate", preferred_language="fr")
        db.add(user)
        try:
            db.flush()
        except IntegrityError:
            # Two first requests at once (e.g. React StrictMode): the other one created the row.
            db.rollback()
            user = db.scalars(select(User).where(User.email == email)).one()
    now = datetime.now(UTC)
    if user.last_login_at is None or now - user.last_login_at >= LAST_LOGIN_EVERY:
        user.last_login_at = now
        db.commit()
    return user


def has_profile(db: Session, user_id: uuid.UUID) -> bool:
    return db.scalar(select(Candidate.id).where(Candidate.user_id == user_id)) is not None
