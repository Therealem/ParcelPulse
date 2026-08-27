"""Compatibility entry point for applying Alembic migrations."""

from pathlib import Path

from alembic import command
from alembic.config import Config

_BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]


def create_database_tables() -> None:
    """Apply all pending migrations through Alembic."""
    alembic_config = Config(str(_BACKEND_DIRECTORY / "alembic.ini"))
    command.upgrade(alembic_config, "head")


def create_shipment_table() -> None:
    """Apply migrations through the original compatibility helper name."""
    create_database_tables()


if __name__ == "__main__":
    create_database_tables()
    print("ParcelPulse database is at the latest Alembic revision.")
