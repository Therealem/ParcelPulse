"""Shipment persistence operations."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Shipment
from app.schemas.tracking import TrackingLookupResponse


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
    return session.get(Shipment, shipment_id)
