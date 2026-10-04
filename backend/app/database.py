from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set to the Supabase PostgreSQL connection string")

    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        raise RuntimeError("DATABASE_URL must use PostgreSQL with the psycopg driver")
    if "sslmode" not in url.query:
        url = url.update_query_dict({"sslmode": "require"})

    return create_engine(url, pool_pre_ping=True, pool_recycle=1800)


@lru_cache
def _get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def SessionLocal() -> Session:
    return _get_session_factory()()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()