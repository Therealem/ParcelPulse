"""Tests for safe, idempotent Shippo tracking webhook ingestion."""

import hashlib
import hmac
import json
from pathlib import Path
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import ShippoWebhookSettings, get_shippo_webhook_settings
from app.main import app
from app.models import Shipment, TrackingEvent, User
from app.services.tracking_service import TrackingService
from app.tracking_providers.mock_provider import MockTrackingProvider

UPS_TRACKING_NUMBER = "1Z999AA10123456784"
USPS_TRACKING_NUMBER = "9400111899223856928499"
WEBHOOK_PATH = "/api/webhooks/shippo"
HMAC_SECRET = "shippo-hmac-test-secret-not-real"

client = TestClient(app)


@pytest.fixture(autouse=True)
def unverified_local_webhooks() -> None:
    """Keep webhook verification disabled unless a test enables it."""
    settings = ShippoWebhookSettings(
        APP_ENV="development",
        SHIPPO_WEBHOOK_SECRET=None,
        SHIPPO_WEBHOOK_HMAC_SECRET=None,
        _env_file=None,
    )
    app.dependency_overrides[get_shippo_webhook_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_shippo_webhook_settings, None)


def shippo_tracker_payload(
    *,
    status: str = "TRANSIT",
    detail: str = "Package departed the carrier facility.",
    status_date: str = "2026-08-30T15:30:00Z",
    tracking_number: str = UPS_TRACKING_NUMBER,
) -> dict[str, Any]:
    """Build a representative canonical Shippo tracker object."""
    location = {
        "city": "Fort Worth",
        "state": "TX",
        "zip": "76102",
        "country": "US",
    }
    current = {
        "status": status,
        "status_details": detail,
        "location": location,
        "status_date": status_date,
    }
    return {
        "carrier": "ups",
        "tracking_number": tracking_number,
        "eta": "2026-09-01T20:00:00Z",
        "tracking_history": [
            {
                "status": "PRE_TRANSIT",
                "status_details": "The carrier received shipment details.",
                "location": None,
                "status_date": "2026-08-28T10:15:00Z",
            },
            current,
        ],
        "tracking_status": current,
    }


def webhook_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    """Wrap one tracker object in Shippo's documented event envelope."""
    return {"event": "track_updated", "test": False, "data": payload}


def enable_hmac_verification(
    *,
    secret: str | None = HMAC_SECRET,
    environment: str = "development",
    tolerance_seconds: int = 300,
) -> None:
    """Require a synthetic HMAC secret for one isolated test."""
    settings = ShippoWebhookSettings(
        APP_ENV=environment,
        SHIPPO_WEBHOOK_HMAC_SECRET=secret,
        SHIPPO_WEBHOOK_HMAC_TOLERANCE_SECONDS=tolerance_seconds,
        _env_file=None,
    )
    app.dependency_overrides[get_shippo_webhook_settings] = lambda: settings


def serialize_webhook(envelope: dict[str, Any], *, pretty: bool = False) -> bytes:
    """Create stable raw JSON bytes for signing and request delivery."""
    if pretty:
        return json.dumps(envelope, indent=2).encode("utf-8")
    return json.dumps(envelope, separators=(",", ":")).encode("utf-8")


def shippo_signature(
    body: bytes,
    *,
    timestamp: int | None = None,
    secret: str = HMAC_SECRET,
) -> str:
    """Sign raw bytes using Shippo's documented HMAC format."""
    signed_at = int(time.time()) if timestamp is None else timestamp
    signed_payload = str(signed_at).encode("ascii") + b"." + body
    digest = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    return f"t={signed_at},v1={digest}"


def post_signed_webhook(
    envelope: dict[str, Any],
    *,
    body: bytes | None = None,
    timestamp: int | None = None,
    secret: str = HMAC_SECRET,
):
    """Post one correctly shaped synthetic Shippo HMAC request."""
    request_body = serialize_webhook(envelope) if body is None else body
    return client.post(
        WEBHOOK_PATH,
        content=request_body,
        headers={
            "Content-Type": "application/json",
            "Shippo-Auth-Signature": shippo_signature(
                request_body,
                timestamp=timestamp,
                secret=secret,
            ),
        },
    )


def save_mock_shipment(tracking_number: str = UPS_TRACKING_NUMBER) -> dict:
    response = client.post(
        "/api/tracking",
        json={"tracking_number": tracking_number},
    )
    assert response.status_code == 200
    return response.json()


def test_delivered_webhook_updates_shipment() -> None:
    saved = save_mock_shipment()
    payload = shippo_tracker_payload(
        status="DELIVERED",
        detail="Package delivered at the front door.",
        status_date="2026-08-31T18:45:00Z",
    )

    response = client.post(WEBHOOK_PATH, json=webhook_envelope(payload))
    detail = client.get(f"/api/shipments/{saved['id']}")

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "Delivered"
    assert body["latest_update"] == "Package delivered at the front door."
    assert body["estimated_delivery"] == "September 1, 2026"
    assert body["tracking_events"][0]["status"] == "Delivered"


def test_in_transit_webhook_updates_shipment() -> None:
    saved = save_mock_shipment()

    response = client.post(
        WEBHOOK_PATH,
        json=webhook_envelope(shippo_tracker_payload()),
    )
    detail = client.get(f"/api/shipments/{saved['id']}").json()

    assert response.status_code == 200
    assert detail["status"] == "In Transit"
    assert detail["latest_update"] == (
        "Package departed the carrier facility."
    )


def test_multiple_tracking_events_are_normalized_newest_first() -> None:
    saved = save_mock_shipment()
    payload = shippo_tracker_payload()
    payload["tracking_history"].insert(
        1,
        {
            "status": "TRANSIT",
            "status_details": "Package arrived at the regional facility.",
            "location": {
                "city": "Dallas",
                "state": "TX",
                "country": "US",
            },
            "status_date": "2026-08-29T12:00:00Z",
        },
    )

    response = client.post(WEBHOOK_PATH, json=webhook_envelope(payload))
    events = client.get(
        f"/api/shipments/{saved['id']}"
    ).json()["tracking_events"]

    assert response.status_code == 200
    assert len(events) == 3
    assert [event["event_time"] for event in events] == sorted(
        (event["event_time"] for event in events),
        reverse=True,
    )
    assert events[1]["location"] == "Dallas, TX, US"


def test_duplicate_webhook_is_idempotent_and_duplicate_free() -> None:
    saved = save_mock_shipment()
    envelope = webhook_envelope(shippo_tracker_payload())

    first = client.post(WEBHOOK_PATH, json=envelope)
    first_events = client.get(
        f"/api/shipments/{saved['id']}"
    ).json()
    second = client.post(WEBHOOK_PATH, json=envelope)
    second_detail = client.get(
        f"/api/shipments/{saved['id']}"
    ).json()

    assert first.status_code == second.status_code == 200
    assert [event["id"] for event in second_detail["tracking_events"]] == [
        event["id"] for event in first_events["tracking_events"]
    ]
    assert len(second_detail["tracking_events"]) == 2
    assert second_detail["updated_at"] == first_events["updated_at"]


def test_unknown_tracking_number_is_safely_ignored(
    isolated_database: sessionmaker[Session],
) -> None:
    payload = shippo_tracker_payload(tracking_number="1Z1111111111111111")

    response = client.post(WEBHOOK_PATH, json=webhook_envelope(payload))

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}
    with isolated_database() as session:
        count = session.scalar(select(func.count()).select_from(Shipment))
    assert count == 0


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        (b"{not-json", "application/json"),
        (b'{"event":"track_updated"}', "application/json"),
        (b'{"event":"   ","data":{}}', "application/json"),
    ],
)
def test_malformed_webhook_returns_clean_4xx(
    body: bytes,
    content_type: str,
) -> None:
    response = client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"Content-Type": content_type},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid webhook payload"}
    assert "not-json" not in response.text


def test_real_webhook_replaces_old_mock_timeline(
    isolated_database: sessionmaker[Session],
) -> None:
    saved = save_mock_shipment()
    mock_event_ids = {
        event["id"] for event in saved["tracking_events"]
    }

    response = client.post(
        WEBHOOK_PATH,
        json=webhook_envelope(shippo_tracker_payload()),
    )

    assert response.status_code == 200
    with isolated_database() as session:
        events = list(
            session.scalars(
                select(TrackingEvent).where(
                    TrackingEvent.shipment_id == saved["id"]
                )
            ).all()
        )
    assert len(events) == 2
    assert mock_event_ids.isdisjoint(event.id for event in events)


def test_webhook_preserves_ownership_and_unrelated_shipments(
    isolated_database: sessionmaker[Session],
) -> None:
    target = save_mock_shipment()
    unrelated = save_mock_shipment(USPS_TRACKING_NUMBER)
    with isolated_database() as session:
        target_owner = session.scalar(
            select(Shipment.user_id).where(Shipment.id == target["id"])
        )
        unrelated_before = session.get(Shipment, unrelated["id"])
        assert unrelated_before is not None
        unrelated_status = unrelated_before.status

    response = client.post(
        WEBHOOK_PATH,
        json=webhook_envelope(shippo_tracker_payload()),
    )

    assert response.status_code == 200
    with isolated_database() as session:
        updated = session.get(Shipment, target["id"])
        untouched = session.get(Shipment, unrelated["id"])
        assert updated is not None
        assert untouched is not None
        assert updated.user_id == target_owner
        assert untouched.status == unrelated_status


def test_webhook_updates_separate_owned_copies_without_changing_owners(
    isolated_database: sessionmaker[Session],
) -> None:
    first = save_mock_shipment()
    with isolated_database() as session:
        second_user = User(
            email="webhook-owner-two@parcelpulse.test",
            password_hash="unused-test-hash",
        )
        session.add(second_user)
        session.commit()
        session.refresh(second_user)
        second = TrackingService(
            session,
            MockTrackingProvider(),
        ).track(UPS_TRACKING_NUMBER, second_user.id)
        second_id = second.id
        first_owner = session.scalar(
            select(Shipment.user_id).where(Shipment.id == first["id"])
        )
        assert first_owner is not None
        owner_ids = {first["id"]: first_owner, second_id: second_user.id}

    payload = shippo_tracker_payload(
        status="DELIVERED",
        detail="Package delivered.",
        status_date="2026-08-31T18:45:00Z",
    )
    response = client.post(WEBHOOK_PATH, json=webhook_envelope(payload))

    assert response.status_code == 200
    with isolated_database() as session:
        copies = list(
            session.scalars(
                select(Shipment).where(
                    Shipment.id.in_([first["id"], second_id])
                )
            ).all()
        )
        assert len(copies) == 2
        assert all(shipment.status == "Delivered" for shipment in copies)
        assert all(
            shipment.user_id == owner_ids[shipment.id]
            for shipment in copies
        )


def test_optional_relay_secret_rejects_unverified_request() -> None:
    save_mock_shipment()
    settings = ShippoWebhookSettings(
        SHIPPO_WEBHOOK_SECRET="test-relay-credential",
        _env_file=None,
    )
    app.dependency_overrides[get_shippo_webhook_settings] = lambda: settings
    envelope = webhook_envelope(shippo_tracker_payload())

    rejected = client.post(WEBHOOK_PATH, json=envelope)
    accepted = client.post(
        WEBHOOK_PATH,
        json=envelope,
        headers={
            "X-ParcelPulse-Webhook-Secret": "test-relay-credential"
        },
    )

    assert rejected.status_code == 401
    assert rejected.json() == {"detail": "Webhook authentication failed"}
    assert accepted.status_code == 200


def test_valid_shippo_hmac_signature_updates_shipment() -> None:
    saved = save_mock_shipment()
    enable_hmac_verification(environment="production")
    envelope = webhook_envelope(
        shippo_tracker_payload(
            status="DELIVERED",
            detail="Package delivered at the front door.",
            status_date="2026-08-31T18:45:00Z",
        )
    )

    response = post_signed_webhook(envelope)
    shipment = client.get(f"/api/shipments/{saved['id']}").json()

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}
    assert shipment["status"] == "Delivered"


def test_shippo_hmac_uses_exact_raw_body_bytes() -> None:
    save_mock_shipment()
    enable_hmac_verification()
    envelope = webhook_envelope(shippo_tracker_payload())
    pretty_body = serialize_webhook(envelope, pretty=True)

    response = post_signed_webhook(envelope, body=pretty_body)

    assert response.status_code == 200


def test_shippo_hmac_rejects_missing_signature() -> None:
    save_mock_shipment()
    enable_hmac_verification()
    body = serialize_webhook(webhook_envelope(shippo_tracker_payload()))

    response = client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Webhook authentication failed"}


def test_shippo_hmac_rejects_tampered_body() -> None:
    save_mock_shipment()
    enable_hmac_verification()
    original = webhook_envelope(shippo_tracker_payload())
    tampered = webhook_envelope(
        shippo_tracker_payload(
            status="DELIVERED",
            detail="Forged delivery status.",
        )
    )
    original_body = serialize_webhook(original)
    tampered_body = serialize_webhook(tampered)

    response = client.post(
        WEBHOOK_PATH,
        content=tampered_body,
        headers={
            "Content-Type": "application/json",
            "Shippo-Auth-Signature": shippo_signature(original_body),
        },
    )

    assert response.status_code == 401
    shipments = client.get("/api/shipments").json()
    assert shipments[0]["status"] == "In Transit"


def test_shippo_hmac_rejects_wrong_secret() -> None:
    save_mock_shipment()
    enable_hmac_verification()
    envelope = webhook_envelope(shippo_tracker_payload())

    response = post_signed_webhook(
        envelope,
        secret="different-test-secret",
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Webhook authentication failed"}


@pytest.mark.parametrize(
    "signature_header",
    [
        "",
        "t=not-a-timestamp,v1=" + "0" * 64,
        "t=1788290000",
        "t=1788290000,v1=not-hex",
        "t=1788290000,v1=" + "0" * 64 + ",extra=value",
        "t=1788290000,t=1788290000,v1=" + "0" * 64,
    ],
)
def test_shippo_hmac_rejects_malformed_signature_header(
    signature_header: str,
) -> None:
    enable_hmac_verification()
    body = serialize_webhook(webhook_envelope(shippo_tracker_payload()))

    response = client.post(
        WEBHOOK_PATH,
        content=body,
        headers={
            "Content-Type": "application/json",
            "Shippo-Auth-Signature": signature_header,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Webhook authentication failed"}


@pytest.mark.parametrize("offset_seconds", [-3600, 3600])
def test_shippo_hmac_rejects_timestamp_outside_tolerance(
    offset_seconds: int,
) -> None:
    enable_hmac_verification(tolerance_seconds=300)
    envelope = webhook_envelope(shippo_tracker_payload())

    response = post_signed_webhook(
        envelope,
        timestamp=int(time.time()) + offset_seconds,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Webhook authentication failed"}


def test_production_webhook_fails_closed_without_hmac_secret() -> None:
    enable_hmac_verification(secret=None, environment="production")

    response = client.post(
        WEBHOOK_PATH,
        json=webhook_envelope(shippo_tracker_payload()),
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Webhook verification is not configured"
    }


def test_shippo_hmac_failures_do_not_log_or_return_secrets(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "local-hmac-secret-must-never-appear"
    enable_hmac_verification(secret=secret)
    envelope = webhook_envelope(shippo_tracker_payload())

    response = post_signed_webhook(
        envelope,
        secret="incorrect-secret",
    )

    assert response.status_code == 401
    assert secret not in response.text
    assert secret not in caplog.text
    assert "incorrect-secret" not in caplog.text


def test_shippo_hmac_settings_load_from_environment_file(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_ENV=production\n"
        f"SHIPPO_WEBHOOK_HMAC_SECRET={HMAC_SECRET}\n"
        "SHIPPO_WEBHOOK_HMAC_TOLERANCE_SECONDS=180\n",
        encoding="utf-8",
    )

    settings = ShippoWebhookSettings(_env_file=env_file)

    assert settings.app_environment == "production"
    assert settings.hmac_secret is not None
    assert settings.hmac_secret.get_secret_value() == HMAC_SECRET
    assert settings.hmac_tolerance_seconds == 180


def test_non_tracking_webhook_is_safely_ignored() -> None:
    response = client.post(
        WEBHOOK_PATH,
        json={"event": "transaction_updated", "test": False, "data": {}},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}


def test_existing_manual_refresh_still_works() -> None:
    saved = save_mock_shipment()
    client.post(WEBHOOK_PATH, json=webhook_envelope(shippo_tracker_payload()))

    refreshed = client.post(f"/api/shipments/{saved['id']}/refresh")
    repeated = client.post(f"/api/shipments/{saved['id']}/refresh")

    assert refreshed.status_code == repeated.status_code == 200
    assert refreshed.json()["status"] == "In Transit"
    assert len(refreshed.json()["tracking_events"]) == 4
    assert [event["id"] for event in repeated.json()["tracking_events"]] == [
        event["id"] for event in refreshed.json()["tracking_events"]
    ]
