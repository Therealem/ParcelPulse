"""Deterministic mock UPS carrier adapter."""

import re
from datetime import UTC, datetime

from app.carriers.base import (
    CarrierAdapterError,
)
from app.tracking_providers.base import TrackingEventResult, TrackingResult

UPS_TRACKING_PATTERN = re.compile(r"^1Z[A-Z0-9]{16}$")
UPS_MOCK_TRACKING_NUMBER = "1Z999AA10123456784"


class UPSAdapter:
    """Return realistic mock data for UPS-formatted tracking numbers."""

    name = "UPS"

    def supports_tracking_number(self, tracking_number: str) -> bool:
        return UPS_TRACKING_PATTERN.fullmatch(tracking_number) is not None

    def track(self, tracking_number: str) -> TrackingResult:
        if not self.supports_tracking_number(tracking_number):
            raise CarrierAdapterError("UPS does not support this tracking number")

        return TrackingResult(
            tracking_number=tracking_number,
            carrier=self.name,
            status="In Transit",
            estimated_delivery="August 28, 2026",
            latest_update="Package departed carrier facility",
            events=(
                TrackingEventResult(
                    status="Label created",
                    description=(
                        "Shipping label created; UPS is awaiting the package."
                    ),
                    location=None,
                    event_time=datetime(2026, 8, 24, 14, 15, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="Package received by UPS",
                    description=(
                        "Package received by UPS and prepared for transit."
                    ),
                    location="Dallas, TX",
                    event_time=datetime(2026, 8, 25, 20, 40, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="Departed carrier facility",
                    description="Package departed the UPS carrier facility.",
                    location="Dallas, TX",
                    event_time=datetime(2026, 8, 26, 6, 10, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="In transit",
                    description="Package is moving through the UPS network.",
                    location="Fort Worth, TX",
                    event_time=datetime(2026, 8, 26, 15, 30, tzinfo=UTC),
                ),
            ),
        )
