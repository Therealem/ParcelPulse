"""Tests for meaningful, user-owned in-app shipment notifications."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_tracking_service
from app.config import (
    ApplicationSettings,
    ShippoWebhookSettings,
    get_application_settings,
    get_shippo_webhook_settings,
)
from app.database import get_database_session
from app.main import app
from app.models import Notification, Shipment, TrackingEvent, User
from app.services.tracking_service import TrackingService
from app.tracking_providers.base import TrackingEventResult, TrackingResult

UPS_TRACKING_NUMBER = "1Z999AA10123456784"
WEBHOOK_PATH = "/api/webhooks/shippo"

client = TestClient(app)


@pytest.fixture(autouse=True)
def unverified_local_webhooks() -> None:
    """Keep verification disabled for isolated synthetic webhook tests."""
    settings = ShippoWebhookSettings(
        SHIPPO_WEBHOOK_SECRET=None,
        _env_file=None,
    )
    app.dependency_overrides[get_shippo_webhook_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_shippo_webhook_settings, None)


def save_mock_shipment() -> dict[str, Any]:
    response = client.post(
        "/api/tracking",
        json={"tracking_number": UPS_TRACKING_NUMBER},
    )
    assert response.status_code == 200
    return response.json()


def shippo_webhook(
    status: str,
    detail: str,
    *,
    status_date: str = "2026-08-31T18:45:00Z",
) -> dict[str, Any]:
    location = {
        "city": "Fort Worth",
        "state": "TX",
        "country": "US",
    }
    current = {
        "status": status,
        "status_details": detail,
        "location": location,
        "status_date": status_date,
    }
    return {
        "event": "track_updated",
        "test": True,
        "data": {
            "carrier": "ups",
            "tracking_number": UPS_TRACKING_NUMBER,
            "eta": "2026-09-01T20:00:00Z",
            "tracking_history": [current],
            "tracking_status": current,
        },
    }


def post_webhook(status: str, detail: str, **kwargs: str):
    return client.post(
        WEBHOOK_PATH,
        json=shippo_webhook(status, detail, **kwargs),
    )


def test_delivered_transition_creates_notification() -> None:
    save_mock_shipment()

    response = post_webhook("DELIVERED", "Package delivered at the door.")
    notifications = client.get("/api/notifications")

    assert response.status_code == 200
    assert notifications.status_code == 200
    assert notifications.json() == [
        {
            "id": notifications.json()[0]["id"],
            "type": "delivered",
            "title": "Package delivered",
            "message": "Your UPS package was delivered.",
            "is_read": False,
            "created_at": notifications.json()[0]["created_at"],
        }
    ]


def test_out_for_delivery_transition_creates_notification() -> None:
    save_mock_shipment()

    response = post_webhook("TRANSIT", "Package is out for delivery.")
    notification = client.get("/api/notifications").json()[0]

    assert response.status_code == 200
    assert notification["type"] == "out_for_delivery"
    assert notification["title"] == "Out for delivery"
    assert notification["message"] == (
        "Your UPS package is out for delivery."
    )


@pytest.mark.parametrize(
    ("status", "detail", "expected_type"),
    [
        ("TRANSIT", "Severe weather caused a delivery delay.", "delayed"),
        ("FAILURE", "A delivery exception occurred.", "exception"),
        ("RETURNED", "Package returned to sender.", "returned"),
    ],
)
def test_delay_exception_and_return_create_notifications(
    status: str,
    detail: str,
    expected_type: str,
) -> None:
    save_mock_shipment()

    response = post_webhook(status, detail)
    notifications = client.get("/api/notifications").json()

    assert response.status_code == 200
    assert len(notifications) == 1
    assert notifications[0]["type"] == expected_type


def test_ordinary_in_transit_scan_does_not_create_notification() -> None:
    save_mock_shipment()

    response = post_webhook(
        "TRANSIT",
        "Package arrived at the regional carrier facility.",
    )

    assert response.status_code == 200
    assert client.get("/api/notifications").json() == []
    assert client.get("/api/notifications/unread-count").json() == {
        "unread_count": 0
    }


def test_duplicate_webhook_does_not_duplicate_notification() -> None:
    save_mock_shipment()
    payload = shippo_webhook("DELIVERED", "Package delivered at the door.")

    first = client.post(WEBHOOK_PATH, json=payload)
    second = client.post(WEBHOOK_PATH, json=payload)

    assert first.status_code == second.status_code == 200
    assert len(client.get("/api/notifications").json()) == 1


class DeliveredProvider:
    """Deterministic provider used to exercise manual refresh transitions."""

    name = "test-delivered"

    def track(self, tracking_number: str, carrier: str) -> TrackingResult:
        event_time = datetime(2026, 8, 31, 18, 45, tzinfo=UTC)
        event = TrackingEventResult(
            status="Delivered",
            description="Package delivered at the door.",
            location="Fort Worth, TX",
            event_time=event_time,
        )
        return TrackingResult(
            tracking_number=tracking_number,
            carrier=carrier,
            status="Delivered",
            estimated_delivery="August 31, 2026",
            latest_update="Package delivered at the door.",
            events=(event,),
        )


class OrdinaryTransitProvider:
    """Provider result that changes scan details, but not meaningful status."""

    name = "test-in-transit"

    def track(self, tracking_number: str, carrier: str) -> TrackingResult:
        event_time = datetime(2026, 8, 31, 16, 15, tzinfo=UTC)
        event = TrackingEventResult(
            status="In Transit",
            description="Package arrived at the regional carrier facility.",
            location="Fort Worth, TX",
            event_time=event_time,
        )
        return TrackingResult(
            tracking_number=tracking_number,
            carrier=carrier,
            status="In Transit",
            estimated_delivery="September 1, 2026",
            latest_update=event.description,
            events=(event,),
        )


def test_status_change_after_manual_refresh_notifies_owner_once(
    isolated_database: sessionmaker[Session],
) -> None:
    shipment = save_mock_shipment()

    def delivered_tracking_service(
        session: Session = Depends(get_database_session),
    ) -> TrackingService:
        return TrackingService(session, DeliveredProvider())

    app.dependency_overrides[get_tracking_service] = delivered_tracking_service
    try:
        first = client.post(f"/api/shipments/{shipment['id']}/refresh")
        second = client.post(f"/api/shipments/{shipment['id']}/refresh")
    finally:
        app.dependency_overrides.pop(get_tracking_service, None)

    assert first.status_code == second.status_code == 200
    notifications = client.get("/api/notifications").json()
    assert len(notifications) == 1
    assert notifications[0]["type"] == "delivered"

    with isolated_database() as session:
        saved_shipment = session.get(Shipment, shipment["id"])
        notification = session.scalar(select(Notification))

    assert saved_shipment is not None
    assert notification is not None
    assert notification.user_id == saved_shipment.user_id
    assert notification.shipment_id == saved_shipment.id


def test_ordinary_manual_refresh_does_not_create_notification() -> None:
    shipment = save_mock_shipment()

    def transit_tracking_service(
        session: Session = Depends(get_database_session),
    ) -> TrackingService:
        return TrackingService(session, OrdinaryTransitProvider())

    app.dependency_overrides[get_tracking_service] = transit_tracking_service
    try:
        response = client.post(f"/api/shipments/{shipment['id']}/refresh")
    finally:
        app.dependency_overrides.pop(get_tracking_service, None)

    assert response.status_code == 200
    assert response.json()["status"] == "In Transit"
    assert response.json()["latest_update"] == (
        "Package arrived at the regional carrier facility."
    )
    assert client.get("/api/notifications").json() == []


def register(auth_client: TestClient, email: str) -> None:
    response = auth_client.post(
        "/api/auth/register",
        json={"email": email, "password": "Strong-Test-Password-123!"},
    )
    assert response.status_code == 201


def track_ups(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/tracking",
        json={"tracking_number": UPS_TRACKING_NUMBER},
    )
    assert response.status_code == 200


def test_notifications_belong_to_each_matching_shipment_owner(
    auth_client: TestClient,
    isolated_database: sessionmaker[Session],
) -> None:
    register(auth_client, "first-notifications@example.com")
    track_ups(auth_client)
    auth_client.post("/api/auth/logout")
    register(auth_client, "second-notifications@example.com")
    track_ups(auth_client)

    delivered = auth_client.post(
        WEBHOOK_PATH,
        json=shippo_webhook("DELIVERED", "Package delivered."),
    )

    assert delivered.status_code == 200
    with isolated_database() as session:
        notifications = list(session.scalars(select(Notification)).all())
        users = list(session.scalars(select(User)).all())
    notified_user_ids = {notification.user_id for notification in notifications}
    created_user_ids = {
        user.id
        for user in users
        if user.email.endswith("-notifications@example.com")
    }
    assert len(notifications) == 2
    assert notified_user_ids == created_user_ids


def test_user_cannot_read_or_modify_another_users_notification(
    auth_client: TestClient,
) -> None:
    register(auth_client, "notification-owner@example.com")
    track_ups(auth_client)
    auth_client.post(
        WEBHOOK_PATH,
        json=shippo_webhook("DELIVERED", "Package delivered."),
    )
    notification_id = auth_client.get("/api/notifications").json()[0]["id"]

    auth_client.post("/api/auth/logout")
    register(auth_client, "notification-other@example.com")

    assert auth_client.get("/api/notifications").json() == []
    assert auth_client.get("/api/notifications/unread-count").json() == {
        "unread_count": 0
    }
    response = auth_client.patch(
        f"/api/notifications/{notification_id}/read"
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Notification not found"}


def create_two_notifications() -> list[dict[str, Any]]:
    save_mock_shipment()
    first = post_webhook(
        "TRANSIT",
        "Package is out for delivery.",
        status_date="2026-08-31T10:00:00Z",
    )
    second = post_webhook(
        "DELIVERED",
        "Package delivered at the door.",
        status_date="2026-08-31T18:45:00Z",
    )
    assert first.status_code == second.status_code == 200
    return client.get("/api/notifications").json()


def test_unread_count_and_mark_one_read_work() -> None:
    notifications = create_two_notifications()

    assert [item["type"] for item in notifications] == [
        "delivered",
        "out_for_delivery",
    ]
    assert client.get("/api/notifications/unread-count").json() == {
        "unread_count": 2
    }

    marked = client.patch(
        f"/api/notifications/{notifications[1]['id']}/read"
    )

    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    assert client.get("/api/notifications/unread-count").json() == {
        "unread_count": 1
    }


def test_mark_all_read_only_updates_current_users_notifications() -> None:
    notifications = create_two_notifications()

    response = client.patch("/api/notifications/read-all")

    assert response.status_code == 200
    assert response.json() == {"updated_count": 2}
    assert client.get("/api/notifications/unread-count").json() == {
        "unread_count": 0
    }
    assert all(
        notification["is_read"]
        for notification in client.get("/api/notifications").json()
    )
    assert len(notifications) == 2


def test_notification_endpoints_require_authentication(
    auth_client: TestClient,
) -> None:
    assert auth_client.get("/api/notifications").status_code == 401
    assert (
        auth_client.get("/api/notifications/unread-count").status_code == 401
    )
    assert auth_client.patch("/api/notifications/read-all").status_code == 401
    assert auth_client.patch("/api/notifications/1/read").status_code == 401


def test_notification_deduplication_constraint_is_enforced(
    isolated_database: sessionmaker[Session],
) -> None:
    save_mock_shipment()
    payload = shippo_webhook("DELIVERED", "Package delivered.")
    client.post(WEBHOOK_PATH, json=payload)
    client.post(WEBHOOK_PATH, json=payload)

    with isolated_database() as session:
        count = session.scalar(select(func.count()).select_from(Notification))
    assert count == 1


def development_settings(
    *,
    enabled: bool,
    environment: str = "development",
) -> ApplicationSettings:
    return ApplicationSettings(
        APP_ENV=environment,
        ENABLE_DEV_NOTIFICATION_ENDPOINT=enabled,
        FRONTEND_ORIGIN="http://localhost:3000",
        _env_file=None,
    )


def test_development_notification_endpoint_is_disabled_by_default() -> None:
    settings = development_settings(enabled=False)
    app.dependency_overrides[get_application_settings] = lambda: settings
    try:
        status_response = client.get("/api/notifications/dev/status")
        response = client.post("/api/notifications/dev/test")
    finally:
        app.dependency_overrides.pop(get_application_settings, None)

    assert status_response.status_code == 404
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


def test_development_notification_endpoint_is_never_enabled_in_production(
) -> None:
    settings = development_settings(enabled=True, environment="production")
    app.dependency_overrides[get_application_settings] = lambda: settings
    try:
        status_response = client.get("/api/notifications/dev/status")
        response = client.post("/api/notifications/dev/test")
    finally:
        app.dependency_overrides.pop(get_application_settings, None)

    assert status_response.status_code == 404
    assert response.status_code == 404


def test_development_notification_does_not_modify_shipments(
    isolated_database: sessionmaker[Session],
) -> None:
    saved = save_mock_shipment()
    with isolated_database() as session:
        shipment_before = session.get(Shipment, saved["id"])
        assert shipment_before is not None
        shipment_snapshot = (
            shipment_before.tracking_number,
            shipment_before.carrier,
            shipment_before.status,
            shipment_before.estimated_delivery,
            shipment_before.latest_update,
            shipment_before.updated_at,
        )
        event_ids_before = tuple(
            session.scalars(
                select(TrackingEvent.id)
                .where(TrackingEvent.shipment_id == saved["id"])
                .order_by(TrackingEvent.id)
            ).all()
        )

    settings = development_settings(enabled=True)
    app.dependency_overrides[get_application_settings] = lambda: settings
    try:
        status_response = client.get("/api/notifications/dev/status")
        response = client.post("/api/notifications/dev/test")
    finally:
        app.dependency_overrides.pop(get_application_settings, None)

    assert status_response.status_code == 200
    assert status_response.json() == {"enabled": True}
    assert response.status_code == 201
    assert response.json()["type"] == "test"
    assert response.json()["title"] == "Development test notification"
    assert "development-only" in response.json()["message"]
    assert response.json()["is_read"] is False
    assert "shipment_id" not in response.json()

    with isolated_database() as session:
        notification = session.scalar(select(Notification))
        shipment_after = session.get(Shipment, saved["id"])
        assert notification is not None
        assert notification.shipment_id is None
        assert shipment_after is not None
        assert (
            shipment_after.tracking_number,
            shipment_after.carrier,
            shipment_after.status,
            shipment_after.estimated_delivery,
            shipment_after.latest_update,
            shipment_after.updated_at,
        ) == shipment_snapshot
        event_ids_after = tuple(
            session.scalars(
                select(TrackingEvent.id)
                .where(TrackingEvent.shipment_id == saved["id"])
                .order_by(TrackingEvent.id)
            ).all()
        )
    assert event_ids_after == event_ids_before


def test_development_notification_requires_authentication(
    auth_client: TestClient,
) -> None:
    settings = development_settings(enabled=True)
    app.dependency_overrides[get_application_settings] = lambda: settings
    try:
        status_response = auth_client.get("/api/notifications/dev/status")
        response = auth_client.post("/api/notifications/dev/test")
    finally:
        app.dependency_overrides.pop(get_application_settings, None)

    assert status_response.status_code == 401
    assert response.status_code == 401
