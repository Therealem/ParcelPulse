"""Shipment persistence operations."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models import Shipment, TrackingEvent
from app.schemas.tracking import TrackingLookupResponse

MOCK_UPS_TRACKING_EVENTS = (
    {
        "status": "Label created",
        "description": "Shipping label created; UPS is awaiting the package.",
        "location": None,
        "event_time": datetime(2026, 8, 24, 14, 15, tzinfo=UTC),
    },
    {
        "status": "Package received by UPS",
        "description": "Package received by UPS and prepared for transit.",
        "location": "Dallas, TX",
        "event_time": datetime(2026, 8, 25, 20, 40, tzinfo=UTC),
    },
    {
        "status": "Departed carrier facility",
        "description": "Package departed the UPS carrier facility.",
        "location": "Dallas, TX",
        "event_time": datetime(2026, 8, 26, 6, 10, tzinfo=UTC),
    },
    {
        "status": "In transit",
        "description": "Package is moving through the UPS network.",
        "location": "Fort Worth, TX",
        "event_time": datetime(2026, 8, 26, 15, 30, tzinfo=UTC),
    },
)


def add_mock_tracking_events(
    shipment: Shipment,
    carrier: str,
) -> None:
    """Seed one mock UPS history without duplicating existing events."""
    if carrier != "UPS" or shipment.tracking_events:
        return

    shipment.tracking_events.extend(
        TrackingEvent(**event) for event in MOCK_UPS_TRACKING_EVENTS
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
