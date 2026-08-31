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
from app.tracking_providers.base import (
    MalformedProviderResponseError,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnsupportedCarrierError,
    TrackingNotFoundError,
)

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
    if isinstance(error, ProviderConfigurationError):
        logger.error("Tracking provider configuration is invalid")
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The tracking provider is not configured",
        )
    if isinstance(error, ProviderAuthenticationError):
        logger.warning("Tracking provider authentication failed")
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The tracking provider could not authenticate",
        )
    if isinstance(error, TrackingNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracking number was not found",
        )
    if isinstance(error, ProviderUnsupportedCarrierError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The tracking provider does not support this carrier",
        )
    if isinstance(error, ProviderTimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The tracking provider timed out",
        )
    if isinstance(error, ProviderRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The tracking provider rate limit was reached",
        )
    if isinstance(
        error,
        (ProviderUnavailableError, MalformedProviderResponseError),
    ):
        logger.warning(
            "Tracking provider failure: %s",
            type(error).__name__,
        )
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The tracking provider is temporarily unavailable",
        )

    logger.error("Tracking persistence failure: %s", type(error).__name__)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Tracking data could not be saved",
    )
