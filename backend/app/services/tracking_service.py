"""Application service for carrier lookups and idempotent persistence."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.carriers import (
    CARRIER_ADAPTERS,
    CarrierAdapter,
    CarrierAdapterError,
    TrackingEventResult,
    TrackingResult,
    detect_carrier,
    normalize_tracking_number,
)
from app.models import Shipment, TrackingEvent


class TrackingPersistenceError(Exception):
    """Raised when normalized tracking data cannot be saved safely."""


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
        adapters: Sequence[CarrierAdapter] = CARRIER_ADAPTERS,
    ) -> None:
        self.session = session
        self.adapters = adapters

    def track(self, tracking_number: str, user_id: int) -> Shipment:
        """Look up and upsert one authenticated user's shipment."""
        normalized_number = normalize_tracking_number(tracking_number)
        adapter = detect_carrier(normalized_number, self.adapters)
        result = self._call_adapter(adapter, normalized_number)

        shipment = self._find_owned_shipment(user_id, normalized_number)
        shipment = self._apply_result(shipment, result, user_id)

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
            shipment = self._apply_result(shipment, result, user_id)
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

    def _call_adapter(
        self,
        adapter: CarrierAdapter,
        tracking_number: str,
    ) -> TrackingResult:
        try:
            result = adapter.track(tracking_number)
        except CarrierAdapterError:
            raise
        except Exception as error:
            raise CarrierAdapterError(
                f"{adapter.name} tracking adapter failed"
            ) from error

        if (
            result.tracking_number != tracking_number
            or result.carrier != adapter.name
        ):
            raise CarrierAdapterError(
                f"{adapter.name} returned an invalid tracking result"
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
        if shipment is None:
            shipment = Shipment(
                user_id=user_id,
                tracking_number=result.tracking_number,
                carrier=result.carrier,
                status=result.status,
                estimated_delivery=result.estimated_delivery,
                latest_update=result.latest_update,
            )
            self.session.add(shipment)
        else:
            shipment.carrier = result.carrier
            shipment.status = result.status
            shipment.estimated_delivery = result.estimated_delivery
            shipment.latest_update = result.latest_update
            shipment.updated_at = datetime.now(UTC)

        self._merge_events(shipment, result.events)
        return shipment

    @staticmethod
    def _merge_events(
        shipment: Shipment,
        events: tuple[TrackingEventResult, ...],
    ) -> None:
        existing = {
            _event_identity(
                event.status,
                event.description,
                event.event_time,
            )
            for event in shipment.tracking_events
        }
        for event in events:
            identity = _event_identity(
                event.status,
                event.description,
                event.event_time,
            )
            if identity in existing:
                continue
            shipment.tracking_events.append(
                TrackingEvent(
                    status=event.status,
                    description=event.description,
                    location=event.location,
                    event_time=event.event_time,
                )
            )
            existing.add(identity)
