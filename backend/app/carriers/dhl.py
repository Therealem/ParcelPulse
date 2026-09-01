"""Deterministic mock DHL carrier adapter."""

import re
from datetime import UTC, datetime

from app.carriers.base import (
    CarrierAdapterError,
)
from app.carriers.usps import is_usps_tracking_number
from app.tracking_providers.base import TrackingEventResult, TrackingResult

DHL_TRACKING_PATTERN = re.compile(
    r"^(?:\d{10}|JJD\d{16,20}|JD\d{16,20}|GM\d{16,18})$"
)
DHL_MOCK_TRACKING_NUMBER = "1234567890"


class DHLAdapter:
    """Return realistic mock data for DHL-formatted tracking numbers."""

    name = "DHL"

    def supports_tracking_number(self, tracking_number: str) -> bool:
        return bool(
            DHL_TRACKING_PATTERN.fullmatch(tracking_number)
            and not is_usps_tracking_number(tracking_number)
        )

    def track(self, tracking_number: str) -> TrackingResult:
        if not self.supports_tracking_number(tracking_number):
            raise CarrierAdapterError("DHL does not support this tracking number")

        return TrackingResult(
            tracking_number=tracking_number,
            carrier=self.name,
            status="Customs Cleared",
            estimated_delivery="August 31, 2026",
            latest_update="Clearance processing completed at destination",
            events=(
                TrackingEventResult(
                    status="Shipment information received",
                    description="DHL received the shipment details from the sender.",
                    location="Frankfurt, Germany",
                    event_time=datetime(2026, 8, 22, 10, 20, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="Shipment picked up",
                    description="DHL Express collected the shipment.",
                    location="Frankfurt, Germany",
                    event_time=datetime(2026, 8, 23, 17, 40, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="Departed DHL facility",
                    description="Shipment departed the DHL Express hub.",
                    location="Leipzig, Germany",
                    event_time=datetime(2026, 8, 24, 22, 15, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="Customs clearance complete",
                    description=(
                        "Clearance processing completed at the destination gateway."
                    ),
                    location="Cincinnati, OH",
                    event_time=datetime(2026, 8, 26, 8, 55, tzinfo=UTC),
                ),
            ),
        )
