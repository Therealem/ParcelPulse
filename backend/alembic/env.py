"""Alembic environment configured from ParcelPulse database settings."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, create_engine, pool

from app.database.config import get_database_settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def configure_context(connection: Connection) -> None:
    """Configure and run migrations on an established connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Render migration SQL without creating a database connection."""
    context.configure(
        url=get_database_settings().sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against PostgreSQL or a supplied test connection."""
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        configure_context(supplied_connection)
        return

    engine = create_engine(
        get_database_settings().sqlalchemy_url,
        poolclass=pool.NullPool,
        pool_pre_ping=True,
    )
    with engine.connect() as connection:
        configure_context(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
