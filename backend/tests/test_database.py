"""Tests for database configuration and health reporting."""

from typing import Self

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.database.config import DatabaseSettings
from app.main import app

client = TestClient(app)


class HealthyConnection:
    """Minimal context-managed connection used by the health endpoint test."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, statement: object) -> None:
        assert str(statement) == "SELECT 1"


class HealthyEngine:
    def connect(self) -> HealthyConnection:
        return HealthyConnection()


class UnavailableEngine:
    def connect(self) -> None:
        raise SQLAlchemyError("database unavailable")


def test_database_settings_build_psycopg_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_HOST", "localhost")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.setenv("DATABASE_NAME", "parcelpulse")
    monkeypatch.setenv("DATABASE_USER", "parcelpulse_app")
    monkeypatch.setenv("DATABASE_PASSWORD", "test-password")

    settings = DatabaseSettings(_env_file=None)

    assert settings.sqlalchemy_url.drivername == "postgresql+psycopg"
    assert settings.sqlalchemy_url.host == "localhost"
    assert settings.sqlalchemy_url.port == 5432
    assert settings.sqlalchemy_url.database == "parcelpulse"
    assert settings.sqlalchemy_url.username == "parcelpulse_app"


def test_database_health_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.main.get_engine", lambda: HealthyEngine())

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_database_health_check_reports_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main.get_engine", lambda: UnavailableEngine())

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {"status": "error", "database": "unavailable"}
    }
