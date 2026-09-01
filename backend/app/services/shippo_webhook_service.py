"""Persistence service for normalized Shippo tracking webhooks."""

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models import Shipment
from app.services.notification_service import (
    NotificationPersistenceError,
    create_shipment_transition_notification,
)
from app.services.tracking_service import apply_tracking_result
from app.tracking_providers.base import TrackingResult


class ShippoWebhookPersistenceError(Exception):
    """Raised when a valid webhook cannot be persisted safely."""


def apply_shippo_tracking_update(
    session: Session,
    result: TrackingResult,
) -> bool:
    """Update all owned copies matching one carrier tracking identity."""
    statement = (
        select(Shipment)
        .options(selectinload(Shipment.tracking_events))
        .where(
            Shipment.user_id.is_not(None),
            Shipment.tracking_number == result.tracking_number,
            Shipment.carrier == result.carrier,
        )
        .with_for_update()
    )
    try:
        shipments = list(session.scalars(statement).all())
        if not shipments:
            return False

        for shipment in shipments:
            create_shipment_transition_notification(
                session,
                shipment,
                result,
            )
            apply_tracking_result(shipment, result)
        session.commit()
    except (NotificationPersistenceError, SQLAlchemyError) as error:
        session.rollback()
        raise ShippoWebhookPersistenceError(
            "Shippo webhook update could not be saved"
        ) from error
    return True
