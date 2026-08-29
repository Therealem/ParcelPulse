"""Response builders shared by shipment and tracking routes."""

from app.models import Shipment
from app.schemas.tracking import (
    ShipmentDetailResponse,
    ShipmentResponse,
    TrackingEventResponse,
)
from app.services.shipment_service import ordered_tracking_events


def shipment_detail_response(shipment: Shipment) -> ShipmentDetailResponse:
    """Serialize one shipment with newest-first tracking events."""
    return ShipmentDetailResponse(
        **ShipmentResponse.model_validate(shipment).model_dump(),
        tracking_events=[
            TrackingEventResponse.model_validate(event)
            for event in ordered_tracking_events(shipment)
        ],
    )
