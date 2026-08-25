"""Tracking lookup API routes."""

from fastapi import APIRouter

from app.schemas.tracking import TrackingLookupRequest, TrackingLookupResponse
from app.services.carrier_detection import detect_carrier

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


@router.post("/lookup", response_model=TrackingLookupResponse)
def lookup_tracking(payload: TrackingLookupRequest) -> TrackingLookupResponse:
    """Return mock shipment data for a normalized tracking number."""
    return TrackingLookupResponse(
        tracking_number=payload.tracking_number,
        carrier=detect_carrier(payload.tracking_number),
        status="In Transit",
        estimated_delivery="August 28, 2026",
        latest_update="Package departed carrier facility",
    )
