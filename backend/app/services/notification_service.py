"""Centralized shipment-notification transitions and user operations."""

from dataclasses import dataclass
import hashlib
import secrets

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Notification, Shipment
from app.tracking_providers.base import TrackingEventResult, TrackingResult


class NotificationPersistenceError(Exception):
    """Raised when notification data cannot be read or saved safely."""


@dataclass(frozen=True, slots=True)
class NotificationContent:
    """User-facing content for one meaningful shipment state."""

    type: str
    title: str
    message: str


def create_development_test_notification(
    session: Session,
    user_id: int,
) -> Notification:
    """Create one shipment-independent alert for local end-to-end testing."""
    notification = Notification(
        user_id=user_id,
        shipment_id=None,
        type="test",
        title="Development test notification",
        message=(
            "This development-only notification confirms that ParcelPulse "
            "in-app notifications are working."
        ),
        deduplication_key=secrets.token_hex(32),
    )
    session.add(notification)
    try:
        session.commit()
        session.refresh(notification)
    except SQLAlchemyError as error:
        session.rollback()
        raise NotificationPersistenceError(
            "Test notification could not be created"
        ) from error
    return notification


def create_shipment_transition_notification(
    session: Session,
    shipment: Shipment,
    result: TrackingResult,
) -> Notification | None:
    """Create one alert when an owned shipment enters a meaningful state."""
    if shipment.id is None or shipment.user_id is None:
        return None

    previous_type = _meaningful_type(
        shipment.status,
        shipment.latest_update,
    )
    current_type = _meaningful_type(
        result.status,
        result.latest_update,
    )
    if current_type is None or current_type == previous_type:
        return None
    current_event = _current_meaningful_event(result, current_type)

    content = _content_for(current_type, result.carrier)
    deduplication_key = _deduplication_key(
        shipment.id,
        current_type,
        result,
        current_event,
    )
    try:
        existing = session.scalar(
            select(Notification.id).where(
                Notification.user_id == shipment.user_id,
                Notification.deduplication_key == deduplication_key,
            )
        )
    except SQLAlchemyError as error:
        raise NotificationPersistenceError(
            "Notification state could not be checked"
        ) from error
    if existing is not None:
        return None

    notification = Notification(
        user_id=shipment.user_id,
        shipment_id=shipment.id,
        type=content.type,
        title=content.title,
        message=content.message,
        deduplication_key=deduplication_key,
    )
    session.add(notification)
    return notification


def list_notifications(session: Session, user_id: int) -> list[Notification]:
    """Return only one user's notifications, newest first."""
    try:
        return list(
            session.scalars(
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(
                    Notification.created_at.desc(),
                    Notification.id.desc(),
                )
            ).all()
        )
    except SQLAlchemyError as error:
        raise NotificationPersistenceError(
            "Notifications could not be loaded"
        ) from error


def unread_notification_count(session: Session, user_id: int) -> int:
    """Count one user's unread notifications."""
    try:
        count = session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
    except SQLAlchemyError as error:
        raise NotificationPersistenceError(
            "Unread notifications could not be counted"
        ) from error
    return int(count or 0)


def mark_notification_read(
    session: Session,
    notification_id: int,
    user_id: int,
) -> Notification | None:
    """Mark one notification read only when it belongs to the user."""
    try:
        notification = session.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        if notification is None:
            return None
        if not notification.is_read:
            notification.is_read = True
            session.commit()
            session.refresh(notification)
        return notification
    except SQLAlchemyError as error:
        session.rollback()
        raise NotificationPersistenceError(
            "Notification could not be updated"
        ) from error


def mark_all_notifications_read(session: Session, user_id: int) -> int:
    """Mark every currently unread notification for one user as read."""
    try:
        result = session.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        raise NotificationPersistenceError(
            "Notifications could not be updated"
        ) from error
    return int(result.rowcount or 0)


def _meaningful_type(*values: str) -> str | None:
    text = " ".join(values).casefold()
    if "returned" in text or "return to sender" in text:
        return "returned"
    if any(
        phrase in text
        for phrase in (
            "delivery exception",
            "exception",
            "failed delivery",
            "delivery failed",
            "unable to deliver",
            "could not be delivered",
        )
    ):
        return "exception"
    if "delay" in text:
        return "delayed"
    if "out for delivery" in text:
        return "out_for_delivery"
    if values and values[0].strip().casefold() == "delivered":
        return "delivered"
    return None


def _current_meaningful_event(
    result: TrackingResult,
    notification_type: str,
) -> TrackingEventResult | None:
    matching = [
        event
        for event in result.events
        if _meaningful_type(event.status, event.description)
        == notification_type
    ]
    return max(matching, key=lambda event: event.event_time, default=None)


def _content_for(notification_type: str, carrier: str) -> NotificationContent:
    templates = {
        "out_for_delivery": NotificationContent(
            type="out_for_delivery",
            title="Out for delivery",
            message=f"Your {carrier} package is out for delivery.",
        ),
        "delivered": NotificationContent(
            type="delivered",
            title="Package delivered",
            message=f"Your {carrier} package was delivered.",
        ),
        "delayed": NotificationContent(
            type="delayed",
            title="Delivery delayed",
            message="Your package may be delayed.",
        ),
        "exception": NotificationContent(
            type="exception",
            title="Delivery exception",
            message=f"Your {carrier} package encountered a delivery exception.",
        ),
        "returned": NotificationContent(
            type="returned",
            title="Returning to sender",
            message=f"Your {carrier} package is being returned to the sender.",
        ),
    }
    return templates[notification_type]


def _deduplication_key(
    shipment_id: int,
    notification_type: str,
    result: TrackingResult,
    event: TrackingEventResult | None,
) -> str:
    event_time = event.event_time.isoformat() if event is not None else ""
    source = "|".join(
        (
            str(shipment_id),
            notification_type,
            result.status.strip().casefold(),
            result.latest_update.strip().casefold(),
            event_time,
        )
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()
