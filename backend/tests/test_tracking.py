"""Tests for mock tracking lookups and carrier detection."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_tracking_service
from app.carriers import (
    AmbiguousCarrierError,
    CarrierAdapterError,
    UnsupportedTrackingNumberError,
    detect_carrier,
    normalize_tracking_number,
)
from app.main import app

client = TestClient(app)


def test_successful_lookup_normalizes_tracking_number() -> None:
    response = client.post(
        "/api/tracking",
        json={"tracking_number": " 1z999aa10 123456784 "},
    )

    assert response.status_code == 200
    result = response.json()
    assert {
        key: result[key]
        for key in (
            "tracking_number",
            "carrier",
            "status",
            "estimated_delivery",
            "latest_update",
        )
    } == {
        "tracking_number": "1Z999AA10123456784",
        "carrier": "UPS",
        "status": "In Transit",
        "estimated_delivery": "August 28, 2026",
        "latest_update": "Package departed carrier facility",
    }
    assert len(result["tracking_events"]) == 4


@pytest.mark.parametrize(
    (
        "tracking_number",
        "carrier",
        "expected_status",
        "estimated_delivery",
        "latest_update",
        "latest_event_status",
        "latest_location",
    ),
    [
        (
            "1Z999AA10123456784",
            "UPS",
            "In Transit",
            "August 28, 2026",
            "Package departed carrier facility",
            "In transit",
            "Fort Worth, TX",
        ),
        (
            "9400111899223856928499",
            "USPS",
            "Arriving On Time",
            "August 29, 2026",
            "Arrived at USPS Regional Destination Facility",
            "Arrived at destination facility",
            "Fort Worth, TX",
        ),
        (
            "123456789012",
            "FedEx",
            "At Local Facility",
            "August 28, 2026",
            "Package arrived at the local FedEx facility",
            "At local facility",
            "Fort Worth, TX",
        ),
        (
            "1234567890",
            "DHL",
            "Customs Cleared",
            "August 31, 2026",
            "Clearance processing completed at destination",
            "Customs clearance complete",
            "Cincinnati, OH",
        ),
    ],
)
def test_lookup_returns_carrier_specific_mock_data(
    tracking_number: str,
    carrier: str,
    expected_status: str,
    estimated_delivery: str,
    latest_update: str,
    latest_event_status: str,
    latest_location: str,
) -> None:
    response = client.post(
        "/api/tracking",
        json={"tracking_number": tracking_number},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["tracking_number"] == tracking_number
    assert result["carrier"] == carrier
    assert result["status"] == expected_status
    assert result["estimated_delivery"] == estimated_delivery
    assert result["latest_update"] == latest_update
    assert len(result["tracking_events"]) == 4
    assert result["tracking_events"][0]["status"] == latest_event_status
    assert result["tracking_events"][0]["location"] == latest_location
    assert all(event["description"] for event in result["tracking_events"])
    event_times = [
        event["event_time"] for event in result["tracking_events"]
    ]
    assert event_times == sorted(event_times, reverse=True)


def test_lookup_allows_local_frontend_origin() -> None:
    response = client.options(
        "/api/tracking",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:3000"
    )
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"tracking_number": ""},
        {"tracking_number": "   \t\n"},
    ],
)
def test_lookup_rejects_missing_or_empty_tracking_number(
    payload: dict[str, str],
) -> None:
    response = client.post("/api/tracking", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "tracking_number",
    [
        "ABC123456",
        "1ZINVALID",
        "12345",
        "NOT-A-TRACKING-NUMBER",
    ],
)
def test_lookup_rejects_unsupported_tracking_number(
    tracking_number: str,
) -> None:
    response = client.post(
        "/api/tracking",
        json={"tracking_number": tracking_number},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Unsupported or invalid tracking number"
    }
    assert client.get("/api/shipments").json() == []


@pytest.mark.parametrize(
    ("tracking_number", "expected_carrier"),
    [
        ("1Z999AA10123456784", "UPS"),
        ("9400111899223856928499", "USPS"),
        ("EA123456789US", "USPS"),
        ("123456789012", "FedEx"),
        ("123456789012345", "FedEx"),
        ("12345678901234567890", "FedEx"),
        ("1234567890123456789012", "FedEx"),
        ("1234567890", "DHL"),
        ("JJD1234567890123456", "DHL"),
    ],
)
def test_carrier_detection(
    tracking_number: str,
    expected_carrier: str,
) -> None:
    normalized = normalize_tracking_number(tracking_number)
    assert detect_carrier(normalized).name == expected_carrier


def test_carrier_detection_rejects_unsupported_number() -> None:
    with pytest.raises(UnsupportedTrackingNumberError):
        detect_carrier("ABC123456")


def test_detector_rejects_ambiguous_matches() -> None:
    class MatchingAdapter:
        def __init__(self, name: str) -> None:
            self.name = name

        def supports_tracking_number(self, tracking_number: str) -> bool:
            return True

        def track(self, tracking_number: str):
            raise AssertionError("Ambiguous adapters must not be called")

    with pytest.raises(AmbiguousCarrierError):
        detect_carrier(
            "AMBIGUOUS",
            (MatchingAdapter("First"), MatchingAdapter("Second")),
        )


def test_legacy_lookup_route_remains_available() -> None:
    response = client.post(
        "/api/tracking/lookup",
        json={"tracking_number": "1Z999AA10123456784"},
    )

    assert response.status_code == 200
    assert response.json()["carrier"] == "UPS"


def test_carrier_adapter_failure_returns_clean_gateway_error() -> None:
    class FailingTrackingService:
        def track(self, tracking_number: str, user_id: int):
            raise CarrierAdapterError("mock carrier outage")

    app.dependency_overrides[get_tracking_service] = FailingTrackingService
    try:
        response = client.post(
            "/api/tracking",
            json={"tracking_number": "1Z999AA10123456784"},
        )
    finally:
        app.dependency_overrides.pop(get_tracking_service, None)

    assert response.status_code == 502
    assert response.json() == {
        "detail": "The carrier tracking service is temporarily unavailable"
    }
