"""Reusable FastAPI authentication dependencies."""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import AuthSettings, get_auth_settings
from app.database import get_database_session
from app.models import User
from app.services.auth_service import decode_session_token


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
