"""Application service for carrier lookups and idempotent persistence."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.carriers import (
    CARRIER_ADAPTERS,
    CarrierAdapter,
    detect_carrier,
    normalize_tracking_number,
)
from app.models import Shipment, TrackingEvent
from app.services.notification_service import (
    NotificationPersistenceError,
    create_shipment_transition_notification,
)
from app.tracking_providers.base import (
    MalformedProviderResponseError,
    ProviderUnavailableError,
    TrackingEventResult,
    TrackingProvider,
    TrackingProviderError,
    TrackingResult,
)


class TrackingPersistenceError(Exception):
    """Raised when normalized tracking data cannot be saved safely."""


def apply_tracking_result(
    shipment: Shipment,
    result: TrackingResult,
) -> bool:
    """Reconcile one existing shipment to a canonical provider result."""
    changed = False
    field_values = {
        "carrier": result.carrier,
        "status": result.status,
        "estimated_delivery": result.estimated_delivery,
        "latest_update": result.latest_update,
    }
    for field, value in field_values.items():
        if getattr(shipment, field) != value:
            setattr(shipment, field, value)
            changed = True

    if sync_tracking_events(shipment, result.events):
        changed = True
    if changed:
        shipment.updated_at = datetime.now(UTC)
    return changed


def sync_tracking_events(
    shipment: Shipment,
    events: tuple[TrackingEventResult, ...],
) -> bool:
    """Reconcile saved events to the provider's canonical history."""
    changed = False
    canonical = {
        _event_identity(event.status, event.description, event.event_time): (
            event
        )
        for event in events
    }
    for persisted in tuple(shipment.tracking_events):
        identity = _event_identity(
            persisted.status,
            persisted.description,
            persisted.event_time,
        )
        current = canonical.pop(identity, None)
        if current is None:
            shipment.tracking_events.remove(persisted)
            changed = True
            continue
        if persisted.location != current.location:
            persisted.location = current.location
            changed = True

    for event in canonical.values():
        shipment.tracking_events.append(
            TrackingEvent(
                status=event.status,
                description=event.description,
                location=event.location,
                event_time=event.event_time,
            )
        )
        changed = True
    return changed


def _utc_event_time(value: datetime) -> datetime:
    """Normalize event timestamps for reliable in-memory identity checks."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _event_identity(
    status: str,
    description: str,
    event_time: datetime,
) -> tuple[str, str, datetime]:
    """Match the database's shipment-event uniqueness constraint."""
    return status, description, _utc_event_time(event_time)


class TrackingService:
    """Coordinate detection, carrier lookup, and user-owned persistence."""

    def __init__(
        self,
        session: Session,
        provider: TrackingProvider,
        adapters: Sequence[CarrierAdapter] = CARRIER_ADAPTERS,
    ) -> None:
        self.session = session
        self.provider = provider
        self.adapters = adapters

    def track(self, tracking_number: str, user_id: int) -> Shipment:
        """Look up and upsert one authenticated user's shipment."""
        normalized_number = normalize_tracking_number(tracking_number)
        adapter = detect_carrier(normalized_number, self.adapters)
        result = self._call_provider(
            normalized_number,
            adapter.name,
        )

        shipment = self._find_owned_shipment(user_id, normalized_number)
        try:
            shipment = self._apply_result(shipment, result, user_id)
        except NotificationPersistenceError as error:
            self.session.rollback()
            raise TrackingPersistenceError(
                "Tracking data could not be saved"
            ) from error

        try:
            self.session.commit()
        except IntegrityError as error:
            # A concurrent request may have inserted the same owned shipment or
            # event after our initial read. Reload and merge against that state.
            self.session.rollback()
            shipment = self._find_owned_shipment(user_id, normalized_number)
            if shipment is None:
                raise TrackingPersistenceError(
                    "Tracking data could not be saved"
                ) from error
            try:
                shipment = self._apply_result(shipment, result, user_id)
            except NotificationPersistenceError as retry_error:
                self.session.rollback()
                raise TrackingPersistenceError(
                    "Tracking data could not be saved"
                ) from retry_error
            try:
                self.session.commit()
            except SQLAlchemyError as retry_error:
                self.session.rollback()
                raise TrackingPersistenceError(
                    "Tracking data could not be saved"
                ) from retry_error
        except SQLAlchemyError as error:
            self.session.rollback()
            raise TrackingPersistenceError(
                "Tracking data could not be saved"
            ) from error

        saved = self._find_owned_shipment(user_id, normalized_number)
        if saved is None:
            raise TrackingPersistenceError("Saved shipment could not be loaded")
        return saved

    def refresh(self, shipment_id: int, user_id: int) -> Shipment | None:
        """Refresh an owned shipment without exposing other users' records."""
        shipment = self.session.scalar(
            select(Shipment).where(
                Shipment.id == shipment_id,
                Shipment.user_id == user_id,
            )
        )
        if shipment is None:
            return None
        return self.track(shipment.tracking_number, user_id)

    def _call_provider(
        self,
        tracking_number: str,
        carrier: str,
    ) -> TrackingResult:
        try:
            result = self.provider.track(tracking_number, carrier)
        except TrackingProviderError:
            raise
        except Exception as error:
            raise ProviderUnavailableError(
                "The tracking provider failed unexpectedly"
            ) from error

        if result.tracking_number != tracking_number or not result.carrier:
            raise MalformedProviderResponseError(
                "The tracking provider returned an invalid result"
            )
        return result

    def _find_owned_shipment(
        self,
        user_id: int,
        tracking_number: str,
    ) -> Shipment | None:
        return self.session.scalar(
            select(Shipment)
            .options(selectinload(Shipment.tracking_events))
            .where(
                Shipment.user_id == user_id,
                Shipment.tracking_number == tracking_number,
            )
        )

    def _apply_result(
        self,
        shipment: Shipment | None,
        result: TrackingResult,
        user_id: int,
    ) -> Shipment:
        existing_shipment = shipment is not None
        if not existing_shipment:
            shipment = Shipment(
                user_id=user_id,
                tracking_number=result.tracking_number,
                carrier="",
                status="",
                estimated_delivery="",
                latest_update="",
            )
            self.session.add(shipment)
        assert shipment is not None
        if existing_shipment:
            create_shipment_transition_notification(
                self.session,
                shipment,
                result,
            )
        apply_tracking_result(shipment, result)
        if existing_shipment:
            # A user-triggered lookup/refresh records that it was attempted,
            # while duplicate webhook deliveries remain persistence no-ops.
            shipment.updated_at = datetime.now(UTC)
        return shipment
