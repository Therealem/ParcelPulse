"""Tracking lookup API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.schemas.tracking import (
    TrackingEventResponse,
    TrackingLookupRequest,
    TrackingLookupResponse,
    TrackingLookupResult,
)
from app.services.carrier_detection import detect_carrier
from app.services.mock_tracking import get_mock_tracking_data
from app.services.shipment_service import (
    ordered_tracking_events,
    save_shipment,
)

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


@router.post("/lookup", response_model=TrackingLookupResult)
def lookup_tracking(
    payload: TrackingLookupRequest,
    session: Session = Depends(get_database_session),
) -> TrackingLookupResult:
    """Return mock shipment data and persist it for later retrieval."""
    carrier = detect_carrier(payload.tracking_number)
    mock_data = get_mock_tracking_data(carrier)
    if mock_data is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported or invalid tracking number",
        )

    lookup = TrackingLookupResponse(
        tracking_number=payload.tracking_number,
        carrier=carrier,
        status=mock_data.status,
        estimated_delivery=mock_data.estimated_delivery,
        latest_update=mock_data.latest_update,
    )
    shipment = save_shipment(session, lookup)
    return TrackingLookupResult(
        **TrackingLookupResponse.model_validate(shipment).model_dump(),
        tracking_events=[
            TrackingEventResponse.model_validate(event)
            for event in ordered_tracking_events(shipment)
        ],
    )
