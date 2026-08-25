"""Tests for mock tracking lookups and carrier detection."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.carrier_detection import detect_carrier

client = TestClient(app)


def test_successful_lookup_normalizes_tracking_number() -> None:
    response = client.post(
        "/api/tracking/lookup",
        json={"tracking_number": " 1z999aa10 123456784 "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "tracking_number": "1Z999AA10123456784",
        "carrier": "UPS",
        "status": "In Transit",
        "estimated_delivery": "August 28, 2026",
        "latest_update": "Package departed carrier facility",
    }


def test_lookup_allows_local_frontend_origin() -> None:
    response = client.options(
        "/api/tracking/lookup",
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
    response = client.post("/api/tracking/lookup", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("tracking_number", "expected_carrier"),
    [
        ("1Z999AA10123456784", "UPS"),
        ("9400111899223856928499", "USPS"),
        ("EA123456789US", "USPS"),
        ("123456789012", "FedEx"),
        ("1234567890", "DHL"),
        ("JJD1234567890123456", "DHL"),
        ("ABC123456", "Unknown"),
    ],
)
def test_carrier_detection(
    tracking_number: str,
    expected_carrier: str,
) -> None:
    assert detect_carrier(tracking_number) == expected_carrier
