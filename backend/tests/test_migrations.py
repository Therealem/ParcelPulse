"""Tests for the Alembic migration chain."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.database.verify_migration_baseline import inspect_schema
from app.models import Base

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
INITIAL_REVISION = "20260827_0001"
AUTH_REVISION = "20260827_0002"


def build_alembic_config() -> Config:
    """Load the backend Alembic configuration for an isolated connection."""
    return Config(str(BACKEND_DIRECTORY / "alembic.ini"))


def test_migration_chain_has_one_expected_head() -> None:
    """The authentication revision follows the initial schema."""
    scripts = ScriptDirectory.from_config(build_alembic_config())

    assert scripts.get_current_head() == AUTH_REVISION
    assert scripts.get_revision(AUTH_REVISION).down_revision == INITIAL_REVISION
    assert scripts.get_revision(INITIAL_REVISION).down_revision is None


def test_initial_migration_upgrade_and_downgrade() -> None:
    """The baseline creates and reverses the schema on an isolated database."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    config = build_alembic_config()

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, INITIAL_REVISION)

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


def test_auth_migration_preserves_existing_shipment_data() -> None:
    """Legacy shipments and events survive the ownership migration unmodified."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    config = build_alembic_config()

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, INITIAL_REVISION)
        connection.execute(
            text(
                """
                INSERT INTO shipments (
                    id, tracking_number, carrier, status,
                    estimated_delivery, latest_update, created_at, updated_at
                ) VALUES (
                    1, '1Z999AA10123456784', 'UPS', 'In Transit',
                    'August 28, 2026', 'Package departed carrier facility',
                    '2026-08-27 10:00:00', '2026-08-27 10:00:00'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO tracking_events (
                    id, shipment_id, status, description, location, event_time,
                    created_at
                ) VALUES (
                    1, 1, 'In transit', 'Package is moving',
                    'Fort Worth, TX', '2026-08-27 12:00:00',
                    '2026-08-27 12:00:00'
                )
                """
            )
        )

        command.upgrade(config, "head")

        inspector = inspect(connection)
        assert "users" in inspector.get_table_names()
        assert "user_id" in {
            column["name"] for column in inspector.get_columns("shipments")
        }
        assert {
            index["name"] for index in inspector.get_indexes("shipments")
        } == {"ix_shipments_user_id"}
        assert {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("shipments")
        } == {"uq_shipments_user_tracking_number"}
        shipment_foreign_keys = inspector.get_foreign_keys("shipments")
        assert shipment_foreign_keys == [
            {
                "name": "fk_shipments_user_id_users",
                "constrained_columns": ["user_id"],
                "referred_schema": None,
                "referred_table": "users",
                "referred_columns": ["id"],
                "options": {"ondelete": "CASCADE"},
            }
        ]
        assert {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("users")
        } == {"uq_users_email"}

        shipment = connection.execute(
            text(
                """
                SELECT tracking_number, carrier, status, estimated_delivery,
                       latest_update, user_id
                FROM shipments
                WHERE id = 1
                """
            )
        ).mappings().one()
        event = connection.execute(
            text(
                "SELECT shipment_id, description FROM tracking_events WHERE id = 1"
            )
        ).mappings().one()

        assert dict(shipment) == {
            "tracking_number": "1Z999AA10123456784",
            "carrier": "UPS",
            "status": "In Transit",
            "estimated_delivery": "August 28, 2026",
            "latest_update": "Package departed carrier facility",
            "user_id": None,
        }
        assert dict(event) == {
            "shipment_id": 1,
            "description": "Package is moving",
        }

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
