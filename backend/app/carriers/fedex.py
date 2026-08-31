"""Deterministic mock FedEx carrier adapter."""

import re
from datetime import UTC, datetime

from app.carriers.base import (
    CarrierAdapterError,
)
from app.carriers.usps import is_usps_tracking_number
from app.tracking_providers.base import TrackingEventResult, TrackingResult

FEDEX_TRACKING_PATTERN = re.compile(r"^(?:\d{12}|\d{15}|\d{20}|\d{22})$")
FEDEX_MOCK_TRACKING_NUMBER = "123456789012"


class FedExAdapter:
    """Return realistic mock data for FedEx-formatted tracking numbers."""

    name = "FedEx"

    def supports_tracking_number(self, tracking_number: str) -> bool:
        return bool(
            FEDEX_TRACKING_PATTERN.fullmatch(tracking_number)
            and not is_usps_tracking_number(tracking_number)
        )

    def track(self, tracking_number: str) -> TrackingResult:
        if not self.supports_tracking_number(tracking_number):
            raise CarrierAdapterError("FedEx does not support this tracking number")

        return TrackingResult(
            tracking_number=tracking_number,
            carrier=self.name,
            status="At Local Facility",
            estimated_delivery="August 28, 2026",
            latest_update="Package arrived at the local FedEx facility",
            events=(
                TrackingEventResult(
                    status="Shipment information sent",
                    description="The shipper sent package information to FedEx.",
                    location=None,
                    event_time=datetime(2026, 8, 23, 18, 30, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="Picked up",
                    description="FedEx picked up the package from the sender.",
                    location="Nashville, TN",
                    event_time=datetime(2026, 8, 24, 23, 10, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="Departed FedEx hub",
                    description="Package departed the FedEx sorting hub.",
                    location="Memphis, TN",
                    event_time=datetime(2026, 8, 25, 9, 45, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="At local facility",
                    description="Package arrived at the local FedEx facility.",
                    location="Fort Worth, TX",
                    event_time=datetime(2026, 8, 26, 12, 35, tzinfo=UTC),
                ),
            ),
        )
