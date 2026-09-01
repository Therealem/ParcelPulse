"""Add user-owned in-app notifications.

Revision ID: 20260831_0003
Revises: 20260827_0002
Create Date: 2026-08-31 00:00:00

This additive migration creates one empty table. Existing users, shipments,
tracking events, and their data are not modified.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260831_0003"
down_revision: str | Sequence[str] | None = "20260827_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create notifications with ownership and deduplication constraints."""
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "is_read",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "deduplication_key",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "deduplication_key",
            name="uq_notifications_user_deduplication_key",
        ),
    )
    op.create_index(
        "ix_notifications_shipment_id",
        "notifications",
        ["shipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_user_read_created_at",
        "notifications",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the notifications feature without changing shipment data."""
    op.drop_index(
        "ix_notifications_user_read_created_at",
        table_name="notifications",
    )
    op.drop_index(
        "ix_notifications_shipment_id",
        table_name="notifications",
    )
    op.drop_table("notifications")
