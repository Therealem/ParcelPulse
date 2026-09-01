"""Shippo HTTP tracking provider and response normalization."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx2
from pydantic import SecretStr

from app.tracking_providers.base import (
    MalformedProviderResponseError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnsupportedCarrierError,
    TrackingEventResult,
    TrackingNotFoundError,
    TrackingResult,
)

SHIPPO_API_BASE_URL = "https://api.goshippo.com"
SHIPPO_API_VERSION = "2018-02-08"
SHIPPO_TIMEOUT = httpx2.Timeout(
    connect=3.0,
    read=10.0,
    write=5.0,
    pool=5.0,
)

_CARRIER_TOKENS = {
    "UPS": "ups",
    "USPS": "usps",
    "FedEx": "fedex",
    "DHL": "dhl_express",
}
_CARRIER_NAMES = {
    "ups": "UPS",
    "usps": "USPS",
    "fedex": "FedEx",
    "dhl": "DHL",
    "dhl_express": "DHL",
    "dhl_ecommerce": "DHL",
}
_STATUS_NAMES = {
    "UNKNOWN": "Unknown",
    "PRE_TRANSIT": "Label Created",
    "TRANSIT": "In Transit",
    "DELIVERED": "Delivered",
    "RETURNED": "Returned",
    "FAILURE": "Delivery Exception",
}


class ShippoProvider:
    """Register and normalize real tracking data through Shippo's API."""

    name = "shippo"

    def __init__(
        self,
        api_token: SecretStr,
        client: httpx2.Client | None = None,
    ) -> None:
        self._api_token = api_token
        self._client = client

    def track(self, tracking_number: str, carrier: str) -> TrackingResult:
        carrier_token = _CARRIER_TOKENS.get(carrier)
        if carrier_token is None:
            raise ProviderUnsupportedCarrierError(
                "Shippo does not support the detected carrier"
            )

        response = self._request_tracking(
            carrier_token,
            tracking_number,
        )
        return self._normalize_response(response, tracking_number)

    def _request_tracking(
        self,
        carrier_token: str,
        tracking_number: str,
    ) -> httpx2.Response:
        url = f"{SHIPPO_API_BASE_URL}/tracks/"
        headers = self._request_headers()
        request_body = {
            "carrier": carrier_token,
            "tracking_number": tracking_number,
        }

        try:
            if self._client is not None:
                response = self._client.post(
                    url,
                    headers=headers,
                    json=request_body,
                    timeout=SHIPPO_TIMEOUT,
                )
            else:
                with httpx2.Client(
                    timeout=SHIPPO_TIMEOUT,
                    follow_redirects=False,
                ) as client:
                    response = client.post(
                        url,
                        headers=headers,
                        json=request_body,
                    )
        except httpx2.TimeoutException as error:
            raise ProviderTimeoutError("Shippo request timed out") from error
        except httpx2.RequestError as error:
            raise ProviderUnavailableError(
                "Shippo could not be reached"
            ) from error

        if response.status_code in (401, 403):
            raise ProviderAuthenticationError(
                "Shippo rejected the configured credentials"
            )
        if response.status_code in (400, 404):
            raise TrackingNotFoundError(
                "Shippo could not find this tracking number"
            )
        if response.status_code == 429:
            raise ProviderRateLimitError("Shippo rate limit reached")
        if response.status_code >= 500:
            raise ProviderUnavailableError("Shippo service is unavailable")
        if response.status_code >= 400:
            raise ProviderUnavailableError("Shippo request failed")

        return response

    def _request_headers(self) -> dict[str, str]:
        """Build Shippo headers without retaining a plaintext token copy."""
        return {
            "Accept": "application/json",
            "Authorization": (
                f"ShippoToken {self._api_token.get_secret_value()}"
            ),
            "SHIPPO-API-VERSION": SHIPPO_API_VERSION,
        }

    def _normalize_response(
        self,
        response: httpx2.Response,
        requested_tracking_number: str,
    ) -> TrackingResult:
        try:
            payload = response.json()
        except ValueError as error:
            raise MalformedProviderResponseError(
                "Shippo returned invalid JSON"
            ) from error
        if not isinstance(payload, Mapping):
            raise MalformedProviderResponseError(
                "Shippo returned an invalid tracking payload"
            )

        return normalize_shippo_tracking_payload(
            payload,
            expected_tracking_number=requested_tracking_number,
        )


def normalize_shippo_tracking_payload(
    payload: Mapping[str, Any],
    *,
    expected_tracking_number: str | None = None,
) -> TrackingResult:
    """Normalize a Shippo tracker payload from HTTP or a webhook."""
    response_number = _required_string(payload, "tracking_number")
    normalized_response_number = "".join(response_number.split()).upper()
    if not normalized_response_number or len(normalized_response_number) > 100:
        raise MalformedProviderResponseError(
            "Shippo returned an invalid tracking number"
        )
    if expected_tracking_number is not None:
        normalized_expected = "".join(
            expected_tracking_number.split()
        ).upper()
        if normalized_response_number != normalized_expected:
            raise MalformedProviderResponseError(
                "Shippo returned a different tracking number"
            )

    carrier_token = _required_string(payload, "carrier").lower()
    carrier = _CARRIER_NAMES.get(carrier_token)
    if carrier is None:
        raise ProviderUnsupportedCarrierError(
            "Shippo returned an unsupported carrier"
        )

    current = _required_mapping(payload, "tracking_status")
    status = _normalize_status(current.get("status"))
    latest_update = _optional_string(current.get("status_details")) or status
    estimated_delivery = _normalize_estimated_delivery(payload.get("eta"))

    history = payload.get("tracking_history")
    if not isinstance(history, list):
        raise MalformedProviderResponseError(
            "Shippo tracking history is invalid"
        )
    events = [_normalize_event(event) for event in history]

    current_event = _normalize_event(current)
    current_identity = (
        current_event.status,
        current_event.description,
        current_event.event_time,
    )
    if all(
        (
            event.status,
            event.description,
            event.event_time,
        )
        != current_identity
        for event in events
    ):
        events.append(current_event)
    events.sort(key=lambda event: event.event_time)

    return TrackingResult(
        tracking_number=normalized_response_number,
        carrier=carrier,
        status=status,
        estimated_delivery=estimated_delivery,
        latest_update=latest_update,
        events=tuple(events),
    )

def _required_mapping(
    payload: Mapping[str, Any],
    field: str,
) -> Mapping[str, Any]:
    value = payload.get(field)
    if not isinstance(value, Mapping):
        raise MalformedProviderResponseError(
            f"Shippo field {field} is missing or invalid"
        )
    return value


def _required_string(payload: Mapping[str, Any], field: str) -> str:
    value = _optional_string(payload.get(field))
    if value is None:
        raise MalformedProviderResponseError(
            f"Shippo field {field} is missing or invalid"
        )
    return value


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_status(value: Any) -> str:
    raw_status = _optional_string(value)
    if raw_status is None:
        raise MalformedProviderResponseError(
            "Shippo tracking status is missing"
        )
    status = _STATUS_NAMES.get(raw_status.upper())
    if status is None:
        raise MalformedProviderResponseError(
            "Shippo returned an unknown tracking status"
        )
    return status


def _normalize_estimated_delivery(value: Any) -> str:
    if value is None or value == "":
        return "Not available"
    eta = _parse_datetime(value, "eta")
    return f"{eta.strftime('%B')} {eta.day}, {eta.year}"


def _normalize_event(value: Any) -> TrackingEventResult:
    if not isinstance(value, Mapping):
        raise MalformedProviderResponseError(
            "Shippo tracking event is invalid"
        )
    status = _normalize_status(value.get("status"))
    description = _optional_string(value.get("status_details")) or status
    return TrackingEventResult(
        status=status,
        description=description,
        location=_normalize_location(value.get("location")),
        event_time=_parse_datetime(value.get("status_date"), "status_date"),
    )


def _normalize_location(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise MalformedProviderResponseError(
            "Shippo tracking location is invalid"
        )
    parts = [
        text
        for field in ("city", "state", "zip", "country")
        if (text := _optional_string(value.get(field))) is not None
    ]
    return ", ".join(parts) or None


def _parse_datetime(value: Any, field: str) -> datetime:
    text = _optional_string(value)
    if text is None:
        raise MalformedProviderResponseError(
            f"Shippo field {field} is missing or invalid"
        )
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise MalformedProviderResponseError(
            f"Shippo field {field} is not a valid date-time"
        ) from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
