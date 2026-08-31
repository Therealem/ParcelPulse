"""Authenticated tracking pipeline API routes."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_tracking_service
from app.api.serialization import shipment_detail_response
from app.api.tracking_errors import tracking_http_error
from app.carriers.base import TrackingPipelineError
from app.models import User
from app.schemas.tracking import ShipmentDetailResponse, TrackingLookupRequest
from app.services.tracking_service import (
    TrackingPersistenceError,
    TrackingService,
)
from app.tracking_providers.base import TrackingProviderError

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


@router.post("", response_model=ShipmentDetailResponse)
@router.post(
    "/lookup",
    response_model=ShipmentDetailResponse,
    deprecated=True,
)
def track_package(
    payload: TrackingLookupRequest,
    current_user: User = Depends(get_current_user),
    tracking_service: TrackingService = Depends(get_tracking_service),
) -> ShipmentDetailResponse:
    """Detect, track, and idempotently save an authenticated user's package."""
    try:
        shipment = tracking_service.track(
            payload.tracking_number,
            current_user.id,
        )
    except (
        TrackingPipelineError,
        TrackingProviderError,
        TrackingPersistenceError,
    ) as error:
        raise tracking_http_error(error) from error

    return shipment_detail_response(shipment)
