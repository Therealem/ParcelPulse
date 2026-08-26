"""SQLAlchemy engine and session lifecycle configuration."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.config import get_database_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create one lazily initialized SQLAlchemy engine per process."""
    settings = get_database_settings()
    return create_engine(
        settings.sqlalchemy_url,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return the reusable SQLAlchemy session factory."""
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def get_database_session() -> Generator[Session, None, None]:
    """Yield a database session and always close it after the request."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
