"""Public, payload-safe webhook ingestion routes."""

import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from json import JSONDecodeError

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import (
    ShippoWebhookSettings,
    get_shippo_webhook_settings,
)
from app.database import get_database_session
from app.schemas.webhooks import ShippoWebhookEnvelope
from app.services.shippo_webhook_service import (
    ShippoWebhookPersistenceError,
    apply_shippo_tracking_update,
)
from app.tracking_providers.base import TrackingProviderError
from app.tracking_providers.shippo_provider import (
    normalize_shippo_tracking_payload,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

_MAX_WEBHOOK_BYTES = 1_000_000
_VERIFICATION_HEADER = "X-ParcelPulse-Webhook-Secret"
_SHIPPO_SIGNATURE_HEADER = "Shippo-Auth-Signature"
_HMAC_SIGNATURE_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def _verify_webhook_request(
    request: Request,
    body: bytes,
    settings: ShippoWebhookSettings,
) -> None:
    """Verify configured relay and native Shippo HMAC credentials."""
    configured = settings.webhook_secret
    if configured is not None:
        provided = request.headers.get(_VERIFICATION_HEADER)
        expected = configured.get_secret_value()
        if provided is None or not secrets.compare_digest(provided, expected):
            logger.warning("Rejected Shippo webhook relay authentication")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook authentication failed",
            )

    hmac_secret = settings.hmac_secret
    if hmac_secret is None:
        if settings.app_environment == "production":
            logger.error("Shippo webhook HMAC is not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Webhook verification is not configured",
            )
        return

    signature_header = request.headers.get(_SHIPPO_SIGNATURE_HEADER)
    timestamp_value, signature = _parse_shippo_signature(signature_header)
    timestamp = int(timestamp_value)
    current_timestamp = int(time.time())
    if abs(current_timestamp - timestamp) > settings.hmac_tolerance_seconds:
        logger.warning("Rejected Shippo webhook outside signature tolerance")
        raise _webhook_authentication_error()

    signed_payload = timestamp_value.encode("ascii") + b"." + body
    expected_signature = hmac.new(
        hmac_secret.get_secret_value().encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature.lower(), expected_signature):
        logger.warning("Rejected Shippo webhook HMAC authentication")
        raise _webhook_authentication_error()


def _parse_shippo_signature(
    signature_header: str | None,
) -> tuple[str, str]:
    """Parse Shippo's documented ``t=<timestamp>,v1=<digest>`` format."""
    if signature_header is None:
        logger.warning("Rejected Shippo webhook without HMAC signature")
        raise _webhook_authentication_error()

    values: dict[str, str] = {}
    for component in signature_header.split(","):
        key, separator, value = component.strip().partition("=")
        if (
            not separator
            or not key
            or not value
            or key in values
        ):
            logger.warning("Rejected malformed Shippo webhook signature")
            raise _webhook_authentication_error()
        values[key] = value

    timestamp_value = values.get("t")
    signature = values.get("v1")
    if (
        set(values) != {"t", "v1"}
        or timestamp_value is None
        or not timestamp_value.isascii()
        or not timestamp_value.isdigit()
        or not 1 <= len(timestamp_value) <= 11
        or signature is None
        or _HMAC_SIGNATURE_PATTERN.fullmatch(signature) is None
    ):
        logger.warning("Rejected malformed Shippo webhook signature")
        raise _webhook_authentication_error()

    return timestamp_value, signature


def _webhook_authentication_error() -> HTTPException:
    """Return one sanitized response for all HMAC authentication failures."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Webhook authentication failed",
    )


def _parse_webhook(body: bytes) -> ShippoWebhookEnvelope:
    """Parse without echoing validation input in error responses."""
    try:
        raw_payload = json.loads(body)
        return ShippoWebhookEnvelope.model_validate(raw_payload)
    except (JSONDecodeError, UnicodeDecodeError, ValidationError, TypeError):
        logger.warning("Rejected malformed Shippo webhook")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        ) from None


async def _validated_webhook(
    request: Request,
    settings: ShippoWebhookSettings = Depends(get_shippo_webhook_settings),
) -> ShippoWebhookEnvelope:
    """Authenticate and parse the request before database processing."""
    body = await request.body()
    if len(body) > _MAX_WEBHOOK_BYTES:
        logger.warning("Rejected oversized Shippo webhook")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Webhook payload is too large",
        )
    _verify_webhook_request(request, body, settings)
    return _parse_webhook(body)


@router.post("/shippo")
def receive_shippo_webhook(
    envelope: ShippoWebhookEnvelope = Depends(_validated_webhook),
    session: Session = Depends(get_database_session),
) -> dict[str, str]:
    """Apply one canonical Shippo tracker update without exposing records."""
    if envelope.event != "track_updated":
        logger.info("Ignored non-tracking Shippo webhook")
        return {"status": "ignored"}
    if envelope.data is None:
        logger.warning("Rejected malformed Shippo tracking webhook")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        )

    try:
        result = normalize_shippo_tracking_payload(envelope.data)
        processed = apply_shippo_tracking_update(session, result)
    except TrackingProviderError as error:
        logger.warning(
            "Rejected invalid Shippo tracking payload: %s",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Shippo tracking payload",
        ) from error
    except ShippoWebhookPersistenceError as error:
        logger.error(
            "Shippo webhook persistence failed: %s",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook could not be processed",
        ) from error

    if not processed:
        logger.info("Ignored Shippo webhook without a matching shipment")
        return {"status": "ignored"}
    logger.info("Processed Shippo tracking webhook")
    return {"status": "processed"}
