"""Deterministic mock tracking data for supported carriers."""

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class MockTrackingEvent:
    """One carrier update in a mock shipment journey."""

    status: str
    description: str
    location: str | None
    event_time: datetime


@dataclass(frozen=True, slots=True)
class MockTrackingData:
    """Current shipment state and its chronological event history."""

    status: str
    estimated_delivery: str
    latest_update: str
    events: tuple[MockTrackingEvent, ...]


MOCK_TRACKING_NUMBERS = {
    "UPS": "1Z999AA10123456784",
    "USPS": "9400111899223856928499",
    "FedEx": "123456789012",
    "DHL": "1234567890",
}

MOCK_TRACKING_DATA = {
    "UPS": MockTrackingData(
        status="In Transit",
        estimated_delivery="August 28, 2026",
        latest_update="Package departed carrier facility",
        events=(
            MockTrackingEvent(
                status="Label created",
                description=(
                    "Shipping label created; UPS is awaiting the package."
                ),
                location=None,
                event_time=datetime(2026, 8, 24, 14, 15, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="Package received by UPS",
                description=(
                    "Package received by UPS and prepared for transit."
                ),
                location="Dallas, TX",
                event_time=datetime(2026, 8, 25, 20, 40, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="Departed carrier facility",
                description="Package departed the UPS carrier facility.",
                location="Dallas, TX",
                event_time=datetime(2026, 8, 26, 6, 10, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="In transit",
                description="Package is moving through the UPS network.",
                location="Fort Worth, TX",
                event_time=datetime(2026, 8, 26, 15, 30, tzinfo=UTC),
            ),
        ),
    ),
    "USPS": MockTrackingData(
        status="Arriving On Time",
        estimated_delivery="August 29, 2026",
        latest_update="Arrived at USPS Regional Destination Facility",
        events=(
            MockTrackingEvent(
                status="Pre-Shipment",
                description=(
                    "Shipping label created; USPS is awaiting the item."
                ),
                location="Los Angeles, CA",
                event_time=datetime(2026, 8, 23, 16, 5, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="USPS in possession of item",
                description="USPS received the package from the sender.",
                location="Los Angeles, CA",
                event_time=datetime(2026, 8, 24, 21, 25, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="Moving through network",
                description="Package departed the USPS regional facility.",
                location="Phoenix, AZ",
                event_time=datetime(2026, 8, 25, 11, 50, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="Arrived at destination facility",
                description=(
                    "Package arrived at the USPS regional destination facility."
                ),
                location="Fort Worth, TX",
                event_time=datetime(2026, 8, 26, 13, 20, tzinfo=UTC),
            ),
        ),
    ),
    "FedEx": MockTrackingData(
        status="At Local Facility",
        estimated_delivery="August 28, 2026",
        latest_update="Package arrived at the local FedEx facility",
        events=(
            MockTrackingEvent(
                status="Shipment information sent",
                description="The shipper sent package information to FedEx.",
                location=None,
                event_time=datetime(2026, 8, 23, 18, 30, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="Picked up",
                description="FedEx picked up the package from the sender.",
                location="Nashville, TN",
                event_time=datetime(2026, 8, 24, 23, 10, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="Departed FedEx hub",
                description="Package departed the FedEx sorting hub.",
                location="Memphis, TN",
                event_time=datetime(2026, 8, 25, 9, 45, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="At local facility",
                description="Package arrived at the local FedEx facility.",
                location="Fort Worth, TX",
                event_time=datetime(2026, 8, 26, 12, 35, tzinfo=UTC),
            ),
        ),
    ),
    "DHL": MockTrackingData(
        status="Customs Cleared",
        estimated_delivery="August 31, 2026",
        latest_update="Clearance processing completed at destination",
        events=(
            MockTrackingEvent(
                status="Shipment information received",
                description="DHL received the shipment details from the sender.",
                location="Frankfurt, Germany",
                event_time=datetime(2026, 8, 22, 10, 20, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="Shipment picked up",
                description="DHL Express collected the shipment.",
                location="Frankfurt, Germany",
                event_time=datetime(2026, 8, 23, 17, 40, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="Departed DHL facility",
                description="Shipment departed the DHL Express hub.",
                location="Leipzig, Germany",
                event_time=datetime(2026, 8, 24, 22, 15, tzinfo=UTC),
            ),
            MockTrackingEvent(
                status="Customs clearance complete",
                description=(
                    "Clearance processing completed at the destination gateway."
                ),
                location="Cincinnati, OH",
                event_time=datetime(2026, 8, 26, 8, 55, tzinfo=UTC),
            ),
        ),
    ),
}


def get_mock_tracking_data(carrier: str) -> MockTrackingData | None:
    """Return mock shipment data for a supported carrier."""
    return MOCK_TRACKING_DATA.get(carrier)
