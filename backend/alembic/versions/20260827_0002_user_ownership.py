"""Add users and per-user shipment ownership.

Revision ID: 20260827_0002
Revises: 20260827_0001
Create Date: 2026-08-27 00:00:01

Existing shipment rows are preserved with a NULL user_id. Application queries
exclude those unassigned legacy rows, while every new lookup supplies a user.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260827_0002"
down_revision: str | Sequence[str] | None = "20260827_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SQLITE_NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}


def upgrade() -> None:
    """Create users and add non-destructive shipment ownership metadata."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "email = lower(trim(email)) AND email <> ''",
            name="ck_users_email_normalized",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    if op.get_bind().dialect.name == "sqlite":
        _upgrade_sqlite()
        return

    op.add_column(
        "shipments",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_shipments_user_id_users",
        "shipments",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_shipments_user_id",
        "shipments",
        ["user_id"],
        unique=False,
    )
    op.drop_constraint(
        "shipments_tracking_number_key",
        "shipments",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_shipments_user_tracking_number",
        "shipments",
        ["user_id", "tracking_number"],
    )


def _upgrade_sqlite() -> None:
    """Exercise the PostgreSQL migration safely in isolated SQLite tests."""
    with op.batch_alter_table(
        "shipments",
        naming_convention=_SQLITE_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.drop_constraint(
            "uq_shipments_tracking_number",
            type_="unique",
        )
        batch_op.create_foreign_key(
            "fk_shipments_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_shipments_user_id",
            ["user_id"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_shipments_user_tracking_number",
            ["user_id", "tracking_number"],
        )


def downgrade() -> None:
    """Remove user ownership; this also removes every user account."""
    if op.get_bind().dialect.name == "sqlite":
        _downgrade_sqlite()
    else:
        op.drop_constraint(
            "uq_shipments_user_tracking_number",
            "shipments",
            type_="unique",
        )
        op.create_unique_constraint(
            "shipments_tracking_number_key",
            "shipments",
            ["tracking_number"],
        )
        op.drop_index("ix_shipments_user_id", table_name="shipments")
        op.drop_constraint(
            "fk_shipments_user_id_users",
            "shipments",
            type_="foreignkey",
        )
        op.drop_column("shipments", "user_id")

    op.drop_table("users")


def _downgrade_sqlite() -> None:
    """Reverse ownership schema changes in isolated SQLite tests."""
    with op.batch_alter_table(
        "shipments",
        naming_convention=_SQLITE_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_shipments_user_tracking_number",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_shipments_tracking_number",
            ["tracking_number"],
        )
        batch_op.drop_index("ix_shipments_user_id")
        batch_op.drop_constraint(
            "fk_shipments_user_id_users",
            type_="foreignkey",
        )
        batch_op.drop_column("user_id")
