"""Provider-independent tracking models, errors, and interface."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


class TrackingProviderError(Exception):
    """Base exception for expected tracking provider failures."""


class ProviderConfigurationError(TrackingProviderError):
    """Raised when the selected provider is not configured safely."""


class ProviderAuthenticationError(TrackingProviderError):
    """Raised when a provider rejects ParcelPulse credentials."""


class TrackingNotFoundError(TrackingProviderError):
    """Raised when the provider cannot find a tracking number."""


class ProviderUnsupportedCarrierError(TrackingProviderError):
    """Raised when a provider does not support the detected carrier."""


class ProviderTimeoutError(TrackingProviderError):
    """Raised when the provider does not respond within configured limits."""


class ProviderRateLimitError(TrackingProviderError):
    """Raised when the provider temporarily rate-limits ParcelPulse."""


class ProviderUnavailableError(TrackingProviderError):
    """Raised for provider network failures or upstream outages."""


class MalformedProviderResponseError(TrackingProviderError):
    """Raised when a provider response cannot be normalized safely."""


@dataclass(frozen=True, slots=True)
class TrackingEventResult:
    """One provider-neutral event in a shipment journey."""

    status: str
    description: str
    location: str | None
    event_time: datetime


@dataclass(frozen=True, slots=True)
class TrackingResult:
    """Provider-neutral current tracking state and chronological history."""

    tracking_number: str
    carrier: str
    status: str
    estimated_delivery: str
    latest_update: str
    events: tuple[TrackingEventResult, ...]


@runtime_checkable
class TrackingProvider(Protocol):
    """Interface implemented by tracking data providers."""

    name: str

    def track(self, tracking_number: str, carrier: str) -> TrackingResult:
        """Return normalized tracking data for a detected carrier."""
        ...
