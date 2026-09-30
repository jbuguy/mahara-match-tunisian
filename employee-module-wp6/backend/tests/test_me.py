import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from app.auth import get_jwks_client
from app.config import Settings, get_settings
from app.db import get_db
from app.main import app
from app.models import User

SUPABASE_URL = "https://test-project.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
KID = "test-key"

PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())


class FakeJwksClient:
    """Stands in for PyJWKClient: always returns our local public key."""

    def __init__(self):
        jwk = ECAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True)
        self.key = jwt.PyJWK({**jwk, "kid": KID, "alg": "ES256"})

    def get_signing_key_from_jwt(self, token):
        return self.key


class FakeSession:
    """Answers db.scalar() calls in order: first the users lookup, then the candidates lookup."""

    def __init__(self, *results):
        self.results = list(results)
        self.added = []
        self.committed = False

    def scalar(self, _statement):
        return self.results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        pass

    def commit(self):
        self.committed = True


def make_token(**overrides) -> str:
    now = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()),
        "email": "Amira.Ben@Example.com",
        "aud": "authenticated",
        "iss": ISSUER,
        "iat": now,
        "exp": now + 3600,
        "role": "authenticated",
        "user_metadata": {"full_name": "Amira Ben Salah"},
    }
    claims.update(overrides)
    return jwt.encode(claims, PRIVATE_KEY, algorithm="ES256", headers={"kid": KID})


@pytest.fixture
def session(client):
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, supabase_url=SUPABASE_URL)
    app.dependency_overrides[get_jwks_client] = FakeJwksClient

    def use(fake: FakeSession) -> FakeSession:
        app.dependency_overrides[get_db] = lambda: fake
        return fake

    return use


def get_me(client, token: str | None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.get("/api/v1/me", headers=headers)


def test_me_with_valid_token_returns_existing_user(client, session):
    user = User(id=uuid.uuid4(), email="amira.ben@example.com", role="candidate", preferred_language="fr")
    db = session(FakeSession(user, uuid.uuid4()))

    response = get_me(client, make_token())

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "email": "amira.ben@example.com",
        "name": "Amira Ben Salah",
        "has_profile": True,
    }
    assert user.last_login_at is not None
    assert db.committed


def test_me_creates_user_on_first_login_with_lowercased_email(client, session):
    db = session(FakeSession(None, None))

    response = get_me(client, make_token())

    assert response.status_code == 200
    assert response.json()["has_profile"] is False
    [created] = db.added
    assert created.email == "amira.ben@example.com"
    assert (created.role, created.preferred_language) == ("candidate", "fr")
    assert created.last_login_at is not None


def test_me_rejects_expired_token(client, session):
    session(FakeSession())
    past = int(time.time()) - 7200
    response = get_me(client, make_token(iat=past, exp=past + 3600))
    assert response.status_code == 401
    assert response.json()["detail"] == "token expired"


def test_me_rejects_wrong_audience(client, session):
    session(FakeSession())
    response = get_me(client, make_token(aud="anon"))
    assert response.status_code == 401


def test_me_rejects_wrong_issuer(client, session):
    session(FakeSession())
    response = get_me(client, make_token(iss="https://other-project.supabase.co/auth/v1"))
    assert response.status_code == 401


def test_me_rejects_hs256_token(client, session):
    session(FakeSession())
    now = int(time.time())
    token = jwt.encode(
        {"sub": "x", "email": "a@b.tn", "aud": "authenticated", "iss": ISSUER, "exp": now + 3600},
        "a-shared-secret-that-is-long-enough-for-hs256",
        algorithm="HS256",
    )
    response = get_me(client, token)
    assert response.status_code == 401


def test_me_without_token_returns_401(client, session):
    session(FakeSession())
    response = get_me(client, None)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
