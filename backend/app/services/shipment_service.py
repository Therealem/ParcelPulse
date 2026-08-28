"""Shipment persistence operations."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models import Shipment, TrackingEvent
from app.schemas.tracking import TrackingLookupResponse
from app.services.mock_tracking import get_mock_tracking_data


def add_mock_tracking_events(
    shipment: Shipment,
    carrier: str,
) -> None:
    """Seed one carrier-specific mock history without duplicate events."""
    mock_data = get_mock_tracking_data(carrier)
    if mock_data is None or shipment.tracking_events:
        return

    shipment.tracking_events.extend(
        TrackingEvent(
            status=event.status,
            description=event.description,
            location=event.location,
            event_time=event.event_time,
        )
        for event in mock_data.events
    )


def ordered_tracking_events(shipment: Shipment) -> list[TrackingEvent]:
    """Return a shipment's tracking events from newest to oldest."""
    return sorted(
        shipment.tracking_events,
        key=lambda event: (event.event_time, event.id),
        reverse=True,
    )


def save_shipment(
    session: Session,
    lookup: TrackingLookupResponse,
    user_id: int,
) -> Shipment:
    """Insert or update one user's shipment for a tracking number."""
    shipment = session.scalar(
        select(Shipment).where(
            Shipment.user_id == user_id,
            Shipment.tracking_number == lookup.tracking_number,
        )
    )

    if shipment is None:
        shipment = Shipment(
            user_id=user_id,
            tracking_number=lookup.tracking_number,
            carrier=lookup.carrier,
            status=lookup.status,
            estimated_delivery=lookup.estimated_delivery,
            latest_update=lookup.latest_update,
        )
        session.add(shipment)
    else:
        shipment.carrier = lookup.carrier
        shipment.status = lookup.status
        shipment.estimated_delivery = lookup.estimated_delivery
        shipment.latest_update = lookup.latest_update
        shipment.updated_at = datetime.now(UTC)

    add_mock_tracking_events(shipment, lookup.carrier)

    try:
        session.commit()
        session.refresh(shipment)
    except SQLAlchemyError:
        session.rollback()
        raise

    return shipment


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
