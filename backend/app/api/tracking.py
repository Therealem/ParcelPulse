"""Tracking lookup API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.schemas.tracking import TrackingLookupRequest, TrackingLookupResponse
from app.services.carrier_detection import detect_carrier
from app.services.shipment_service import save_shipment

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


@router.post("/lookup", response_model=TrackingLookupResponse)
def lookup_tracking(
    payload: TrackingLookupRequest,
    session: Session = Depends(get_database_session),
) -> TrackingLookupResponse:
    """Return mock shipment data and persist it for later retrieval."""
    lookup = TrackingLookupResponse(
        tracking_number=payload.tracking_number,
        carrier=detect_carrier(payload.tracking_number),
        status="In Transit",
        estimated_delivery="August 28, 2026",
        latest_update="Package departed carrier facility",
    )
    shipment = save_shipment(session, lookup)
    return TrackingLookupResponse.model_validate(shipment)
