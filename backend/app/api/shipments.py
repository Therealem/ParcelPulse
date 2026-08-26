"""Saved shipment API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.schemas.tracking import ShipmentResponse
from app.services.shipment_service import get_shipment, list_shipments

router = APIRouter(prefix="/api/shipments", tags=["shipments"])


@router.get("", response_model=list[ShipmentResponse])
def read_shipments(
    session: Session = Depends(get_database_session),
) -> list[ShipmentResponse]:
    """Return all saved shipments."""
    return [
        ShipmentResponse.model_validate(shipment)
        for shipment in list_shipments(session)
    ]


@router.get("/{shipment_id}", response_model=ShipmentResponse)
def read_shipment(
    shipment_id: int,
    session: Session = Depends(get_database_session),
) -> ShipmentResponse:
    """Return one saved shipment by ID."""
    shipment = get_shipment(session, shipment_id)
    if shipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )
    return ShipmentResponse.model_validate(shipment)
