"""Request and response schemas for package tracking lookups."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TrackingLookupRequest(BaseModel):
    """Payload accepted by the mock tracking lookup endpoint."""

    tracking_number: str = Field(
        max_length=200,
        examples=["1Z999AA10123456784"],
    )


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
