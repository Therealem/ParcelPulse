"""Unambiguous carrier detection and tracking-number normalization."""

from collections.abc import Sequence

from app.carriers.base import (
    AmbiguousCarrierError,
    CarrierAdapter,
    EmptyTrackingNumberError,
    InvalidTrackingNumberError,
    UnsupportedTrackingNumberError,
)
from app.carriers.registry import CARRIER_ADAPTERS
from app.carriers.usps import canonicalize_usps_tracking_number

MAX_TRACKING_NUMBER_LENGTH = 100


def normalize_tracking_number(tracking_number: str) -> str:
    """Remove whitespace, normalize case, and validate basic input bounds."""
    normalized = "".join(tracking_number.split()).upper()
    if not normalized:
        raise EmptyTrackingNumberError("Tracking number must not be empty")
    if len(normalized) > MAX_TRACKING_NUMBER_LENGTH:
        raise InvalidTrackingNumberError("Tracking number is too long")
    return canonicalize_usps_tracking_number(normalized)


def detect_carrier(
    tracking_number: str,
    adapters: Sequence[CarrierAdapter] = CARRIER_ADAPTERS,
) -> CarrierAdapter:
    """Return the one adapter matching a normalized tracking number."""
    matches = [
        adapter
        for adapter in adapters
        if adapter.supports_tracking_number(tracking_number)
    ]
    if not matches:
        raise UnsupportedTrackingNumberError(
            "Unsupported or invalid tracking number"
        )
    if len(matches) > 1:
        raise AmbiguousCarrierError(
            "Tracking number matches more than one carrier"
        )
    return matches[0]
