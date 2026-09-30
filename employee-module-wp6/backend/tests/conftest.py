import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user, get_token_claims
from app.db import get_db, get_engine
from app.main import app
from app.models import User


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    """A real database session inside a transaction that is rolled back after the test.

    The app's own commits become savepoints, so nothing a test writes is kept.
    Skipped when DATABASE_URL is missing or the database can't be reached.
    """
    try:
        connection = get_engine().connect()
    except Exception as exc:
        pytest.skip(f"database not reachable ({type(exc).__name__})")
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def signed_in(client, db) -> User:
    """A fresh users row, signed in for every request (token checks are covered in test_me.py)."""
    user = User(id=uuid.uuid4(), email=f"test-{uuid.uuid4().hex[:8]}@example.tn", role="candidate")
    db.add(user)
    db.flush()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user=user, name="Test Candidat")
    app.dependency_overrides[get_token_claims] = lambda: {"email": user.email}
    return user


@pytest.fixture
def signed_out(client):
    """No token, and nothing that could reach Supabase or the database."""
    from app.auth import get_jwks_client
    from app.config import Settings, get_settings

    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, supabase_url="https://x.supabase.co")
    app.dependency_overrides[get_jwks_client] = lambda: None
    app.dependency_overrides[get_db] = lambda: None
