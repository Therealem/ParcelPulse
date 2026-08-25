"""Request and response schemas for package tracking lookups."""

from pydantic import BaseModel, Field, field_validator


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

    tracking_number: str
    carrier: str
    status: str
    estimated_delivery: str
    latest_update: str
