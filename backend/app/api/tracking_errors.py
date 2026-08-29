"""HTTP error mapping for expected tracking pipeline failures."""

import logging

from fastapi import HTTPException, status

from app.carriers import (
    AmbiguousCarrierError,
    CarrierAdapterError,
    EmptyTrackingNumberError,
    InvalidTrackingNumberError,
    UnsupportedTrackingNumberError,
)
from app.services.tracking_service import TrackingPersistenceError

logger = logging.getLogger(__name__)


def tracking_http_error(error: Exception) -> HTTPException:
    """Convert an expected pipeline exception into a stable API response."""
    if isinstance(
        error,
        (
            EmptyTrackingNumberError,
            InvalidTrackingNumberError,
            UnsupportedTrackingNumberError,
            AmbiguousCarrierError,
        ),
    ):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        )
    if isinstance(error, CarrierAdapterError):
        logger.warning("Carrier adapter failure: %s", error)
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The carrier tracking service is temporarily unavailable",
        )

    logger.error("Tracking persistence failure: %s", type(error).__name__)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Tracking data could not be saved",
    )
