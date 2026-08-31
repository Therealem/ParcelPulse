"""Reusable FastAPI authentication dependencies."""

from fastapi import Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.tracking_errors import tracking_http_error
from app.config import (
    AuthSettings,
    get_auth_settings,
    get_tracking_provider_settings,
)
from app.database import get_database_session
from app.models import User
from app.services.auth_service import decode_session_token
from app.services.tracking_service import TrackingService
from app.tracking_providers.base import ProviderConfigurationError
from app.tracking_providers.registry import create_tracking_provider


def get_tracking_service(
    session: Session = Depends(get_database_session),
) -> TrackingService:
    """Build the request-scoped tracking pipeline service."""
    try:
        settings = get_tracking_provider_settings()
        provider = create_tracking_provider(settings)
    except ValidationError as error:
        configuration_error = ProviderConfigurationError(
            "Tracking provider configuration is invalid"
        )
        raise tracking_http_error(configuration_error) from error
    except ProviderConfigurationError as error:
        raise tracking_http_error(error) from error
    return TrackingService(session, provider)


def get_current_user(
    request: Request,
    session: Session = Depends(get_database_session),
    settings: AuthSettings = Depends(get_auth_settings),
) -> User:
    """Resolve the authenticated user from the signed HttpOnly cookie."""
    session_token = request.cookies.get(settings.cookie_name)
    user_id = (
        decode_session_token(session_token, settings)
        if session_token is not None
        else None
    )
    user = session.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user
