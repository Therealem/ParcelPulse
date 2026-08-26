"""Shared isolated database setup for API tests."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_database_session
from app.main import app
from app.models import Base


@pytest.fixture(autouse=True)
def isolated_database() -> Generator[None, None, None]:
    """Run each test against a fresh in-memory SQLite database."""
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)

    def override_database_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_database_session, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
