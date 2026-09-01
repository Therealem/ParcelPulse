"""Public, payload-safe webhook ingestion routes."""

import json
import logging
import secrets
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


def _verify_webhook_request(
    request: Request,
    settings: ShippoWebhookSettings,
) -> None:
    """Verify a relay-provided secret when one has been configured."""
    configured = settings.webhook_secret
    if configured is None:
        return

    provided = request.headers.get(_VERIFICATION_HEADER)
    expected = configured.get_secret_value()
    if provided is None or not secrets.compare_digest(provided, expected):
        logger.warning("Rejected Shippo webhook authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook authentication failed",
        )


async def _parse_webhook(request: Request) -> ShippoWebhookEnvelope:
    """Parse without echoing validation input in error responses."""
    body = await request.body()
    if len(body) > _MAX_WEBHOOK_BYTES:
        logger.warning("Rejected oversized Shippo webhook")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Webhook payload is too large",
        )
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
    _verify_webhook_request(request, settings)
    return await _parse_webhook(request)


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
