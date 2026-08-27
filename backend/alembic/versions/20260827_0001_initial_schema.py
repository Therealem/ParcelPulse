"""Create the initial ParcelPulse schema.

Revision ID: 20260827_0001
Revises:
Create Date: 2026-08-27 00:00:00

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260827_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create shipments and tracking events with current constraints."""
    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracking_number", sa.String(length=100), nullable=False),
        sa.Column("carrier", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column(
            "estimated_delivery",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column("latest_update", sa.Text(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracking_number"),
    )
    op.create_table(
        "tracking_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column(
            "event_time",
            sa.DateTime(timezone=True),
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
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shipment_id",
            "status",
            "description",
            "event_time",
            name="uq_tracking_events_shipment_event",
        ),
    )
    op.create_index(
        op.f("ix_tracking_events_shipment_id"),
        "tracking_events",
        ["shipment_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the initial ParcelPulse schema."""
    op.drop_index(
        op.f("ix_tracking_events_shipment_id"),
        table_name="tracking_events",
    )
    op.drop_table("tracking_events")
    op.drop_table("shipments")
