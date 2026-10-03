from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


database_url = get_settings().database_url
engine_options = {"connect_args": {"check_same_thread": False}} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, pool_pre_ping=True, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()