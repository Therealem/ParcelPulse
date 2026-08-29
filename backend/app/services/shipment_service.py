"""Shipment retrieval and deletion operations."""

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models import Shipment, TrackingEvent


def ordered_tracking_events(shipment: Shipment) -> list[TrackingEvent]:
    """Return a shipment's tracking events from newest to oldest."""
    return sorted(
        shipment.tracking_events,
        key=lambda event: (event.event_time, event.id),
        reverse=True,
    )


def list_shipments(session: Session, user_id: int) -> list[Shipment]:
    """Return one user's saved shipments, newest first."""
    return list(
        session.scalars(
            select(Shipment).where(Shipment.user_id == user_id).order_by(
                Shipment.created_at.desc(),
                Shipment.id.desc(),
            )
        ).all()
    )


def get_shipment(
    session: Session,
    shipment_id: int,
    user_id: int,
) -> Shipment | None:
    """Return a shipment only when it belongs to the requesting user."""
    return session.scalar(
        select(Shipment)
        .options(selectinload(Shipment.tracking_events))
        .where(Shipment.id == shipment_id, Shipment.user_id == user_id)
    )


def delete_shipment(session: Session, shipment_id: int, user_id: int) -> bool:
    """Delete an owned shipment and its related events when present."""
    shipment = get_shipment(session, shipment_id, user_id)
    if shipment is None:
        return False

    session.delete(shipment)
    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise

    return True
