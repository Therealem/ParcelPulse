"""Tests for the Alembic migration chain."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app.database.verify_migration_baseline import inspect_schema
from app.models import Base

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
INITIAL_REVISION = "20260827_0001"


def build_alembic_config() -> Config:
    """Load the backend Alembic configuration for an isolated connection."""
    return Config(str(BACKEND_DIRECTORY / "alembic.ini"))


def test_migration_chain_has_one_expected_head() -> None:
    """The committed initial revision is the sole migration head."""
    scripts = ScriptDirectory.from_config(build_alembic_config())

    assert scripts.get_current_head() == INITIAL_REVISION
    assert scripts.get_revision(INITIAL_REVISION).down_revision is None


def test_initial_migration_upgrade_and_downgrade() -> None:
    """The baseline creates and reverses the schema on an isolated database."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    config = build_alembic_config()

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

        inspector = inspect(connection)
        assert {"alembic_version", "shipments", "tracking_events"} <= set(
            inspector.get_table_names()
        )
        assert {
            index["name"]
            for index in inspector.get_indexes("tracking_events")
        } == {"ix_tracking_events_shipment_id"}

        foreign_keys = inspector.get_foreign_keys("tracking_events")
        assert foreign_keys[0]["referred_table"] == "shipments"
        assert foreign_keys[0]["options"] == {"ondelete": "CASCADE"}

        unique_constraints = inspector.get_unique_constraints("tracking_events")
        assert unique_constraints == [
            {
                "name": "uq_tracking_events_shipment_event",
                "column_names": [
                    "shipment_id",
                    "status",
                    "description",
                    "event_time",
                ],
            }
        ]

        command.downgrade(config, "base")
        remaining_tables = set(inspect(connection).get_table_names())
        assert "shipments" not in remaining_tables
        assert "tracking_events" not in remaining_tables

    engine.dispose()


def test_baseline_verifier_accepts_matching_unversioned_schema() -> None:
    """A matching legacy schema is recognized without changing it."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with engine.connect() as connection:
        current_revision, differences = inspect_schema(connection)

    assert current_revision is None
    assert differences == []
    engine.dispose()
