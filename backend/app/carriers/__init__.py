"""Carrier adapters and shared tracking result types."""

from app.carriers.base import (
    AmbiguousCarrierError,
    CarrierAdapter,
    CarrierAdapterError,
    EmptyTrackingNumberError,
    InvalidTrackingNumberError,
    UnsupportedTrackingNumberError,
)
from app.carriers.detector import detect_carrier, normalize_tracking_number
from app.carriers.registry import CARRIER_ADAPTERS
from app.tracking_providers.base import TrackingEventResult, TrackingResult

__all__ = [
    "AmbiguousCarrierError",
    "CARRIER_ADAPTERS",
    "CarrierAdapter",
    "CarrierAdapterError",
    "EmptyTrackingNumberError",
    "InvalidTrackingNumberError",
    "TrackingEventResult",
    "TrackingResult",
    "UnsupportedTrackingNumberError",
    "detect_carrier",
    "normalize_tracking_number",
]
