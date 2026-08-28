"""Shared isolated database setup for API tests."""

from collections.abc import Generator
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault(
    "AUTH_SECRET_KEY",
    "parcelpulse-test-secret-key-at-least-32-characters",
)

from app.api.dependencies import get_current_user
from app.database import get_database_session
from app.main import app
from app.models import Base, User


@pytest.fixture(autouse=True)
def isolated_database() -> Generator[sessionmaker[Session], None, None]:
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

    with session_factory() as session:
        test_user = User(
            email="existing-tests@parcelpulse.test",
            password_hash="unused-test-hash",
        )
        session.add(test_user)
        session.commit()
        session.refresh(test_user)

    def override_database_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    def override_current_user() -> User:
        return test_user

    app.dependency_overrides[get_database_session] = override_database_session
    app.dependency_overrides[get_current_user] = override_current_user
    try:
        yield session_factory
    finally:
        app.dependency_overrides.pop(get_database_session, None)
        app.dependency_overrides.pop(get_current_user, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def auth_client(
    isolated_database: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    """Use real cookie authentication while retaining the isolated database."""
    current_user_override = app.dependency_overrides.pop(get_current_user)
    with TestClient(app) as client:
        client.cookies.clear()
        yield client
    app.dependency_overrides[get_current_user] = current_user_override
