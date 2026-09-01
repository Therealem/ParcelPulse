"""Validated envelopes for external webhook delivery."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ShippoWebhookEnvelope(BaseModel):
    """Minimal fields shared by Shippo webhook notifications."""

    model_config = ConfigDict(extra="ignore")

    event: str = Field(min_length=1, max_length=100)
    test: bool | None = None
    data: dict[str, Any] | None = None

    @field_validator("event", mode="before")
    @classmethod
    def normalize_event(cls, value: object) -> object:
        """Normalize the documented event discriminator."""
        if isinstance(value, str):
            return value.strip().lower()
        return value
