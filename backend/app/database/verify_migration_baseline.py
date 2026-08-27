"""Read-only verification for baselining an existing ParcelPulse database."""

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection

from app.database.session import get_engine
from app.models import Base

_BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]


def inspect_schema(connection: Connection) -> tuple[str | None, list[object]]:
    """Return the recorded revision and model/schema differences without writes."""
    migration_context = MigrationContext.configure(
        connection,
        opts={"compare_type": True, "compare_server_default": True},
    )
    current_revision = migration_context.get_current_revision()
    differences = compare_metadata(migration_context, Base.metadata)
    return current_revision, differences


def main() -> None:
    """Fail unless the live schema is safe to baseline at the current head."""
    alembic_config = Config(str(_BACKEND_DIRECTORY / "alembic.ini"))
    head_revision = ScriptDirectory.from_config(
        alembic_config
    ).get_current_head()

    with get_engine().connect() as connection:
        current_revision, differences = inspect_schema(connection)

    if current_revision not in {None, head_revision}:
        raise SystemExit(
            "Database is recorded at an unexpected revision "
            f"({current_revision}); do not stamp it."
        )

    if differences:
        print("Database schema does not match the SQLAlchemy models:")
        for difference in differences:
            print(f"- {difference!r}")
        raise SystemExit("Schema differences found; do not stamp this database.")

    print("Database schema matches the SQLAlchemy models.")
    if current_revision is None:
        print(f"Safe to stamp the existing schema at revision {head_revision}.")
    else:
        print(f"Database is already at revision {current_revision}.")


if __name__ == "__main__":
    main()
