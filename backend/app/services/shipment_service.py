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
) -> Shipment:
    """Insert a shipment or update the existing row for its tracking number."""
    shipment = session.scalar(
        select(Shipment).where(
            Shipment.tracking_number == lookup.tracking_number
        )
    )

    if shipment is None:
        shipment = Shipment(
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


def list_shipments(session: Session) -> list[Shipment]:
    """Return all saved shipments, newest first."""
    return list(
        session.scalars(
            select(Shipment).order_by(
                Shipment.created_at.desc(),
                Shipment.id.desc(),
            )
        ).all()
    )


def get_shipment(session: Session, shipment_id: int) -> Shipment | None:
    """Return one shipment by primary key when it exists."""
    return session.scalar(
        select(Shipment)
        .options(selectinload(Shipment.tracking_events))
        .where(Shipment.id == shipment_id)
    )
