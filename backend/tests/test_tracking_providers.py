"""Tests for tracking provider selection and Shippo normalization."""

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import httpx2
import pytest
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.tracking_errors import tracking_http_error
from app.config import TrackingProviderSettings
from app.models import Shipment, TrackingEvent, User
from app.services.shipment_service import ordered_tracking_events
from app.services.tracking_service import TrackingService
from app.tracking_providers.base import (
    MalformedProviderResponseError,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnsupportedCarrierError,
    TrackingNotFoundError,
)
from app.tracking_providers.mock_provider import MockTrackingProvider
from app.tracking_providers.registry import create_tracking_provider
from app.tracking_providers.shippo_provider import ShippoProvider

UPS_TRACKING_NUMBER = "1Z999AA10123456784"
DUMMY_TOKEN = "shippo_test_not_a_real_token"
_MISSING = object()


def shippo_payload(
    carrier: str,
    tracking_number: str,
    *,
    eta: str | None | object = "2026-08-31T20:00:00Z",
    location: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a representative Shippo tracking response."""
    current_location = (
        {
            "city": "Fort Worth",
            "state": "TX",
            "zip": "76102",
            "country": "US",
        }
        if location is None
        else location
    )
    payload: dict[str, Any] = {
        "carrier": carrier,
        "tracking_number": tracking_number,
        "messages": [],
        # Deliberately newest-first to verify provider-side chronological sort.
        "tracking_history": [
            {
                "status": "TRANSIT",
                "status_details": "Package departed the carrier facility.",
                "location": current_location,
                "status_date": "2026-08-28T15:30:00Z",
            },
            {
                "status": "PRE_TRANSIT",
                "status_details": "The carrier received shipment details.",
                "location": None,
                "status_date": "2026-08-27T10:15:00Z",
            },
        ],
        "tracking_status": {
            "status": "TRANSIT",
            "status_details": "Package departed the carrier facility.",
            "location": current_location,
            "status_date": "2026-08-28T15:30:00Z",
        },
    }
    if eta is not _MISSING:
        payload["eta"] = eta
    return payload


def shippo_provider_for_payload(
    payload: dict[str, Any],
) -> tuple[ShippoProvider, httpx2.Client]:
    """Build a Shippo provider using an in-memory HTTP transport."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "POST"
        assert request.url == "https://api.goshippo.com/tracks/"
        assert request.headers["Authorization"] == f"ShippoToken {DUMMY_TOKEN}"
        assert request.headers["SHIPPO-API-VERSION"] == "2018-02-08"
        assert request.headers["Content-Type"].startswith("application/json")
        assert json.loads(request.content) == {
            "carrier": payload["carrier"],
            "tracking_number": payload["tracking_number"],
        }
        return httpx2.Response(200, json=payload)

    client = httpx2.Client(transport=httpx2.MockTransport(handler))
    return ShippoProvider(SecretStr(DUMMY_TOKEN), client), client


def test_shippo_lookup_registers_tracker_with_post() -> None:
    payload = shippo_payload("ups", UPS_TRACKING_NUMBER)
    provider, client = shippo_provider_for_payload(payload)
    try:
        result = provider.track(UPS_TRACKING_NUMBER, "UPS")
    finally:
        client.close()

    assert result.tracking_number == UPS_TRACKING_NUMBER
    assert result.carrier == "UPS"


@pytest.mark.parametrize(
    ("detected_carrier", "shippo_carrier", "tracking_number", "expected"),
    [
        ("UPS", "ups", UPS_TRACKING_NUMBER, "UPS"),
        ("USPS", "usps", "9400111899223856928499", "USPS"),
        ("FedEx", "fedex", "123456789012", "FedEx"),
        ("DHL", "dhl_express", "1234567890", "DHL"),
    ],
)
def test_shippo_carrier_response_normalization(
    detected_carrier: str,
    shippo_carrier: str,
    tracking_number: str,
    expected: str,
) -> None:
    payload = shippo_payload(shippo_carrier, tracking_number)
    provider, client = shippo_provider_for_payload(payload)
    try:
        result = provider.track(tracking_number, detected_carrier)
    finally:
        client.close()

    assert result.tracking_number == tracking_number
    assert result.carrier == expected
    assert result.status == "In Transit"
    assert result.estimated_delivery == "August 31, 2026"
    assert result.latest_update == "Package departed the carrier facility."
    assert [event.status for event in result.events] == [
        "Label Created",
        "In Transit",
    ]
    assert result.events[-1].location == "Fort Worth, TX, 76102, US"
    assert list(result.events) == sorted(
        result.events,
        key=lambda event: event.event_time,
    )


def test_shippo_missing_estimated_delivery_is_safe() -> None:
    payload = shippo_payload(
        "ups",
        UPS_TRACKING_NUMBER,
        eta=_MISSING,
    )
    provider, client = shippo_provider_for_payload(payload)
    try:
        result = provider.track(UPS_TRACKING_NUMBER, "UPS")
    finally:
        client.close()

    assert result.estimated_delivery == "Not available"


def test_shippo_missing_location_is_safe() -> None:
    payload = shippo_payload("ups", UPS_TRACKING_NUMBER)
    payload["tracking_history"][0].pop("location")
    payload["tracking_status"].pop("location")
    provider, client = shippo_provider_for_payload(payload)
    try:
        result = provider.track(UPS_TRACKING_NUMBER, "UPS")
    finally:
        client.close()

    assert result.events[-1].location is None


@pytest.mark.parametrize(
    ("shippo_status", "expected_status"),
    [
        ("UNKNOWN", "Unknown"),
        ("PRE_TRANSIT", "Label Created"),
        ("TRANSIT", "In Transit"),
        ("DELIVERED", "Delivered"),
        ("RETURNED", "Returned"),
        ("FAILURE", "Delivery Exception"),
    ],
)
def test_shippo_status_mapping(
    shippo_status: str,
    expected_status: str,
) -> None:
    payload = shippo_payload("ups", UPS_TRACKING_NUMBER)
    payload["tracking_status"]["status"] = shippo_status
    payload["tracking_status"]["status_details"] = "Current carrier update"
    payload["tracking_status"]["status_date"] = "2026-08-29T10:00:00Z"
    provider, client = shippo_provider_for_payload(payload)
    try:
        result = provider.track(UPS_TRACKING_NUMBER, "UPS")
    finally:
        client.close()

    assert result.status == expected_status
    assert result.events[-1].status == expected_status


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        pytest.param(401, ProviderAuthenticationError, id="invalid-token"),
        pytest.param(404, TrackingNotFoundError, id="tracking-not-found"),
        pytest.param(429, ProviderRateLimitError, id="rate-limit"),
        pytest.param(503, ProviderUnavailableError, id="provider-outage"),
    ],
)
def test_shippo_http_errors_are_classified(
    status_code: int,
    expected_error: type[Exception],
) -> None:
    transport = httpx2.MockTransport(
        lambda request: httpx2.Response(
            status_code,
            json={"detail": "sensitive upstream detail"},
        )
    )
    with httpx2.Client(transport=transport) as client:
        provider = ShippoProvider(SecretStr(DUMMY_TOKEN), client)
        with pytest.raises(expected_error):
            provider.track(UPS_TRACKING_NUMBER, "UPS")


def test_shippo_timeout_is_classified() -> None:
    def timeout(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("upstream timeout", request=request)

    with httpx2.Client(
        transport=httpx2.MockTransport(timeout)
    ) as client:
        provider = ShippoProvider(SecretStr(DUMMY_TOKEN), client)
        with pytest.raises(ProviderTimeoutError):
            provider.track(UPS_TRACKING_NUMBER, "UPS")


def test_tracking_settings_load_shippo_token_from_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TRACKING_PROVIDER", raising=False)
    monkeypatch.delenv("SHIPPO_API_TOKEN", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TRACKING_PROVIDER=shippo\n"
        f"SHIPPO_API_TOKEN={DUMMY_TOKEN}\n",
        encoding="utf-8",
    )

    settings = TrackingProviderSettings(_env_file=env_file)

    assert settings.tracking_provider == "shippo"
    assert settings.shippo_api_token is not None
    assert settings.shippo_api_token.get_secret_value() == DUMMY_TOKEN


def test_shippo_rejects_malformed_response() -> None:
    payload = shippo_payload("ups", UPS_TRACKING_NUMBER)
    payload.pop("tracking_status")
    provider, client = shippo_provider_for_payload(payload)
    try:
        with pytest.raises(MalformedProviderResponseError):
            provider.track(UPS_TRACKING_NUMBER, "UPS")
    finally:
        client.close()


def test_shippo_rejects_unsupported_carrier() -> None:
    transport = httpx2.MockTransport(
        lambda request: pytest.fail("Unsupported carriers must not call Shippo")
    )
    with httpx2.Client(transport=transport) as client:
        provider = ShippoProvider(SecretStr(DUMMY_TOKEN), client)
        with pytest.raises(ProviderUnsupportedCarrierError):
            provider.track("AA123456789GB", "Royal Mail")


def test_mock_provider_preserves_existing_behavior() -> None:
    result = MockTrackingProvider().track(UPS_TRACKING_NUMBER, "UPS")

    assert result.carrier == "UPS"
    assert result.status == "In Transit"
    assert len(result.events) == 4


def test_tracking_provider_defaults_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRACKING_PROVIDER", raising=False)
    monkeypatch.delenv("SHIPPO_API_TOKEN", raising=False)

    settings = TrackingProviderSettings(_env_file=None)
    provider = create_tracking_provider(settings)

    assert settings.tracking_provider == "mock"
    assert isinstance(provider, MockTrackingProvider)


@pytest.mark.parametrize("token", [None, "", "replace_with_shippo_api_token"])
def test_shippo_provider_requires_api_token(token: str | None) -> None:
    settings = TrackingProviderSettings(
        TRACKING_PROVIDER="shippo",
        SHIPPO_API_TOKEN=token,
        _env_file=None,
    )

    with pytest.raises(ProviderConfigurationError):
        create_tracking_provider(settings)


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            ProviderConfigurationError("raw secret"),
            503,
            "The tracking provider is not configured",
        ),
        (
            ProviderAuthenticationError("raw secret"),
            502,
            "The tracking provider could not authenticate",
        ),
        (
            TrackingNotFoundError("raw secret"),
            404,
            "Tracking number was not found",
        ),
        (
            ProviderUnsupportedCarrierError("raw secret"),
            422,
            "The tracking provider does not support this carrier",
        ),
        (
            ProviderTimeoutError("raw secret"),
            504,
            "The tracking provider timed out",
        ),
        (
            ProviderRateLimitError("raw secret"),
            429,
            "The tracking provider rate limit was reached",
        ),
        (
            ProviderUnavailableError("raw secret"),
            502,
            "The tracking provider is temporarily unavailable",
        ),
        (
            MalformedProviderResponseError("raw secret"),
            502,
            "The tracking provider is temporarily unavailable",
        ),
    ],
)
def test_provider_errors_map_to_safe_api_responses(
    error: Exception,
    status_code: int,
    detail: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    response = tracking_http_error(error)

    assert response.status_code == status_code
    assert response.detail == detail
    assert "secret" not in str(response.detail).lower()
    assert "raw secret" not in caplog.text.lower()


def test_refresh_through_shippo_is_idempotent(
    isolated_database: sessionmaker[Session],
) -> None:
    payload = shippo_payload("ups", UPS_TRACKING_NUMBER)
    provider, client = shippo_provider_for_payload(deepcopy(payload))
    try:
        with isolated_database() as session:
            user_id = session.scalar(select(User.id))
            assert user_id is not None
            service = TrackingService(session, provider)

            saved = service.track(UPS_TRACKING_NUMBER, user_id)
            shipment_id = saved.id
            first_event_ids = {
                event.id for event in saved.tracking_events
            }

            refreshed = service.refresh(shipment_id, user_id)
            assert refreshed is not None
            second_event_ids = {
                event.id for event in refreshed.tracking_events
            }
            event_count = session.scalar(
                select(func.count())
                .select_from(TrackingEvent)
                .where(TrackingEvent.shipment_id == shipment_id)
            )
    finally:
        client.close()

    assert first_event_ids == second_event_ids
    assert event_count == 2


def test_shippo_refresh_replaces_mock_history_and_preserves_other_shipments(
    isolated_database: sessionmaker[Session],
) -> None:
    usps_number = "9400111899223856928499"
    payload = shippo_payload("usps", usps_number)
    provider, client = shippo_provider_for_payload(payload)
    try:
        with isolated_database() as session:
            user_id = session.scalar(select(User.id))
            assert user_id is not None
            mock_service = TrackingService(session, MockTrackingProvider())
            target = mock_service.track(usps_number, user_id)
            other = mock_service.track(UPS_TRACKING_NUMBER, user_id)
            target_id = target.id
            other_id = other.id
            mock_event_ids = {
                event.id for event in target.tracking_events
            }

            shippo_service = TrackingService(session, provider)
            refreshed = shippo_service.refresh(target_id, user_id)
            assert refreshed is not None
            first_shippo_event_ids = {
                event.id for event in refreshed.tracking_events
            }

            repeated = shippo_service.refresh(target_id, user_id)
            assert repeated is not None
            repeated_event_ids = {
                event.id for event in repeated.tracking_events
            }

            target_event_count = session.scalar(
                select(func.count())
                .select_from(TrackingEvent)
                .where(TrackingEvent.shipment_id == target_id)
            )
            other_event_count = session.scalar(
                select(func.count())
                .select_from(TrackingEvent)
                .where(TrackingEvent.shipment_id == other_id)
            )
            shipment_count = session.scalar(
                select(func.count()).select_from(Shipment)
            )
            newest_first = ordered_tracking_events(repeated)
    finally:
        client.close()

    assert mock_event_ids.isdisjoint(first_shippo_event_ids)
    assert repeated_event_ids == first_shippo_event_ids
    assert target_event_count == 2
    assert other_event_count == 4
    assert shipment_count == 2
    assert [event.event_time for event in newest_first] == sorted(
        (event.event_time for event in newest_first),
        reverse=True,
    )
