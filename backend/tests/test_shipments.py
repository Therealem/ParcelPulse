"""Tests for persistent shipment storage and retrieval."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

UPS_TRACKING_NUMBER = "1Z999AA10123456784"
MOCK_TRACKING_NUMBERS = [
    UPS_TRACKING_NUMBER,
    "9400111899223856928499",
    "123456789012",
    "1234567890",
]


def save_mock_shipment(tracking_number: str = UPS_TRACKING_NUMBER) -> dict:
    """Create a shipment through the public tracking lookup endpoint."""
    response = client.post(
        "/api/tracking/lookup",
        json={"tracking_number": tracking_number},
    )
    assert response.status_code == 200
    return response.json()


def test_successful_lookup_saves_shipment() -> None:
    lookup = save_mock_shipment()

    response = client.get("/api/shipments")

    assert response.status_code == 200
    shipments = response.json()
    assert len(shipments) == 1
    assert shipments[0]["tracking_number"] == lookup["tracking_number"]
    assert shipments[0]["carrier"] == "UPS"
    assert shipments[0]["status"] == "In Transit"
    assert shipments[0]["estimated_delivery"] == "August 28, 2026"
    assert shipments[0]["latest_update"] == (
        "Package departed carrier facility"
    )
    assert isinstance(shipments[0]["id"], int)
    assert shipments[0]["created_at"]
    assert shipments[0]["updated_at"]


@pytest.mark.parametrize("tracking_number", MOCK_TRACKING_NUMBERS)
def test_repeated_lookup_updates_without_duplicate(
    tracking_number: str,
) -> None:
    save_mock_shipment(tracking_number)
    first_saved = client.get("/api/shipments").json()[0]
    first_detail = client.get(
        f"/api/shipments/{first_saved['id']}"
    ).json()

    save_mock_shipment(tracking_number)
    response = client.get("/api/shipments")
    repeated_detail = client.get(
        f"/api/shipments/{first_saved['id']}"
    ).json()

    assert response.status_code == 200
    shipments = response.json()
    assert len(shipments) == 1
    assert shipments[0]["id"] == first_saved["id"]
    assert shipments[0]["created_at"] == first_saved["created_at"]
    assert len(first_detail["tracking_events"]) == 4
    assert repeated_detail["tracking_events"] == first_detail["tracking_events"]


def test_get_shipment_by_id() -> None:
    save_mock_shipment()
    saved = client.get("/api/shipments").json()[0]

    response = client.get(f"/api/shipments/{saved['id']}")

    assert response.status_code == 200
    detail = response.json()
    assert {
        key: detail[key] for key in saved
    } == saved
    assert [event["status"] for event in detail["tracking_events"]] == [
        "In transit",
        "Departed carrier facility",
        "Package received by UPS",
        "Label created",
    ]
    assert [
        event["event_time"] for event in detail["tracking_events"]
    ] == sorted(
        event["event_time"] for event in detail["tracking_events"]
    )[::-1]
    assert detail["tracking_events"][-1]["location"] is None


def test_get_shipment_returns_404_for_unknown_id() -> None:
    response = client.get("/api/shipments/9999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Shipment not found"}
