import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Candidate, User


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
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return user


def has_profile(db: Session, user_id: uuid.UUID) -> bool:
    return db.scalar(select(Candidate.id).where(Candidate.user_id == user_id)) is not None
