"""Request and response schemas for package tracking lookups."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TrackingLookupRequest(BaseModel):
    """Payload accepted by the mock tracking lookup endpoint."""

    tracking_number: str = Field(
        min_length=1,
        max_length=100,
        examples=["1Z999AA10123456784"],
    )

    @field_validator("tracking_number", mode="before")
    @classmethod
    def normalize_tracking_number(cls, value: object) -> object:
        """Remove whitespace and reject values that contain no characters."""
        if not isinstance(value, str):
            return value

        normalized = "".join(value.split()).upper()
        if not normalized:
            raise ValueError("tracking_number must not be empty")

        return normalized


class TrackingLookupResponse(BaseModel):
    """Mock shipment details returned for a tracking number."""

    model_config = ConfigDict(from_attributes=True)

    tracking_number: str
    carrier: str
    status: str
    estimated_delivery: str
    latest_update: str


class ShipmentResponse(TrackingLookupResponse):
    """A shipment persisted in PostgreSQL."""

    id: int
    created_at: datetime
    updated_at: datetime


class TrackingEventResponse(BaseModel):
    """A persisted status update in a shipment's tracking history."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    status: str
    description: str
    location: str | None
    event_time: datetime
    created_at: datetime


class ShipmentDetailResponse(ShipmentResponse):
    """A persisted shipment together with its tracking history."""

    tracking_events: list[TrackingEventResponse]
