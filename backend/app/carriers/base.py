"""Shared contracts and normalized result types for carrier adapters."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


class TrackingPipelineError(Exception):
    """Base exception for expected tracking pipeline failures."""


class InvalidTrackingNumberError(TrackingPipelineError):
    """Raised when a tracking number cannot be normalized safely."""


class EmptyTrackingNumberError(InvalidTrackingNumberError):
    """Raised when a tracking number contains no non-whitespace characters."""


class UnsupportedTrackingNumberError(TrackingPipelineError):
    """Raised when no registered carrier recognizes a tracking number."""


class AmbiguousCarrierError(TrackingPipelineError):
    """Raised when more than one carrier recognizes a tracking number."""


class CarrierAdapterError(TrackingPipelineError):
    """Raised when a selected carrier adapter cannot produce a result."""


@dataclass(frozen=True, slots=True)
class TrackingEventResult:
    """One normalized event returned by a carrier adapter."""

    status: str
    description: str
    location: str | None
    event_time: datetime


@dataclass(frozen=True, slots=True)
class TrackingResult:
    """Carrier-neutral tracking data returned by every adapter."""

    tracking_number: str
    carrier: str
    status: str
    estimated_delivery: str
    latest_update: str
    events: tuple[TrackingEventResult, ...]


@runtime_checkable
class CarrierAdapter(Protocol):
    """Interface implemented by carrier-specific tracking adapters."""

    name: str

    def supports_tracking_number(self, tracking_number: str) -> bool:
        """Return whether this adapter supports the normalized number."""
        ...

    def track(self, tracking_number: str) -> TrackingResult:
        """Return normalized tracking data for a supported number."""
        ...
