"""Saved shipment API routes."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_tracking_service
from app.api.serialization import shipment_detail_response
from app.api.tracking_errors import tracking_http_error
from app.carriers.base import TrackingPipelineError
from app.database import get_database_session
from app.models import User
from app.schemas.tracking import ShipmentDetailResponse, ShipmentResponse
from app.services.shipment_service import (
    delete_shipment,
    get_shipment,
    list_shipments,
)
from app.services.tracking_service import (
    TrackingPersistenceError,
    TrackingService,
)

router = APIRouter(prefix="/api/shipments", tags=["shipments"])


@router.get("", response_model=list[ShipmentResponse])
def read_shipments(
    session: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> list[ShipmentResponse]:
    """Return the authenticated user's saved shipments."""
    return [
        ShipmentResponse.model_validate(shipment)
        for shipment in list_shipments(session, current_user.id)
    ]


@router.get("/{shipment_id}", response_model=ShipmentDetailResponse)
def read_shipment(
    shipment_id: int,
    session: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> ShipmentDetailResponse:
    """Return one saved shipment and its newest-first tracking history."""
    shipment = get_shipment(session, shipment_id, current_user.id)
    if shipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )

    return shipment_detail_response(shipment)


@router.post(
    "/{shipment_id}/refresh",
    response_model=ShipmentDetailResponse,
)
def refresh_shipment(
    shipment_id: int,
    tracking_service: TrackingService = Depends(get_tracking_service),
    current_user: User = Depends(get_current_user),
) -> ShipmentDetailResponse:
    """Refresh an owned shipment through the centralized tracking pipeline."""
    try:
        shipment = tracking_service.refresh(shipment_id, current_user.id)
    except (TrackingPipelineError, TrackingPersistenceError) as error:
        raise tracking_http_error(error) from error

    if shipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )
    return shipment_detail_response(shipment)


@router.delete(
    "/{shipment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def remove_shipment(
    shipment_id: int,
    session: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete one saved shipment together with its tracking history."""
    if not delete_shipment(session, shipment_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
