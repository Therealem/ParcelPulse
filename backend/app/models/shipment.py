"""Persistent shipment model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.notification import Notification
    from app.models.tracking_event import TrackingEvent
    from app.models.user import User


class Shipment(Base):
    """A tracked shipment saved by a lookup."""

    __tablename__ = "shipments"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "tracking_number",
            name="uq_shipments_user_tracking_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    tracking_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    carrier: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    estimated_delivery: Mapped[str] = mapped_column(String(100), nullable=False)
    latest_update: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
    tracking_events: Mapped[list["TrackingEvent"]] = relationship(
        back_populates="shipment",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="shipment",
        passive_deletes=True,
    )
    user: Mapped["User | None"] = relationship(back_populates="shipments")
