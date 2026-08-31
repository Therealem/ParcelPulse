"""Tracking provider contracts and normalized domain results."""

from app.tracking_providers.base import (
    MalformedProviderResponseError,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnsupportedCarrierError,
    TrackingEventResult,
    TrackingNotFoundError,
    TrackingProvider,
    TrackingProviderError,
    TrackingResult,
)

__all__ = [
    "MalformedProviderResponseError",
    "ProviderAuthenticationError",
    "ProviderConfigurationError",
    "ProviderRateLimitError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "ProviderUnsupportedCarrierError",
    "TrackingEventResult",
    "TrackingNotFoundError",
    "TrackingProvider",
    "TrackingProviderError",
    "TrackingResult",
]
