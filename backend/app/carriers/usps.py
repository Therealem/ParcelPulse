"""Deterministic mock USPS carrier adapter."""

import re
from datetime import UTC, datetime

from app.carriers.base import (
    CarrierAdapterError,
)
from app.tracking_providers.base import TrackingEventResult, TrackingResult

USPS_DOMESTIC_PATTERN = re.compile(r"^9[2345]\d{18,20}$")
USPS_INTERNATIONAL_PATTERN = re.compile(r"^[A-Z]{2}\d{9}US$")
USPS_MOCK_TRACKING_NUMBER = "9400111899223856928499"


def is_usps_tracking_number(tracking_number: str) -> bool:
    """Return whether a normalized number matches a supported USPS format."""
    return bool(
        USPS_DOMESTIC_PATTERN.fullmatch(tracking_number)
        or USPS_INTERNATIONAL_PATTERN.fullmatch(tracking_number)
    )


class USPSAdapter:
    """Return realistic mock data for USPS-formatted tracking numbers."""

    name = "USPS"

    def supports_tracking_number(self, tracking_number: str) -> bool:
        return is_usps_tracking_number(tracking_number)

    def track(self, tracking_number: str) -> TrackingResult:
        if not self.supports_tracking_number(tracking_number):
            raise CarrierAdapterError("USPS does not support this tracking number")

        return TrackingResult(
            tracking_number=tracking_number,
            carrier=self.name,
            status="Arriving On Time",
            estimated_delivery="August 29, 2026",
            latest_update="Arrived at USPS Regional Destination Facility",
            events=(
                TrackingEventResult(
                    status="Pre-Shipment",
                    description=(
                        "Shipping label created; USPS is awaiting the item."
                    ),
                    location="Los Angeles, CA",
                    event_time=datetime(2026, 8, 23, 16, 5, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="USPS in possession of item",
                    description="USPS received the package from the sender.",
                    location="Los Angeles, CA",
                    event_time=datetime(2026, 8, 24, 21, 25, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="Moving through network",
                    description="Package departed the USPS regional facility.",
                    location="Phoenix, AZ",
                    event_time=datetime(2026, 8, 25, 11, 50, tzinfo=UTC),
                ),
                TrackingEventResult(
                    status="Arrived at destination facility",
                    description=(
                        "Package arrived at the USPS regional destination facility."
                    ),
                    location="Fort Worth, TX",
                    event_time=datetime(2026, 8, 26, 13, 20, tzinfo=UTC),
                ),
            ),
        )
