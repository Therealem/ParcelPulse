"""Account registration and cookie-based authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.config import AuthSettings, get_auth_settings
from app.database import get_database_session
from app.models import User
from app.schemas.auth import AuthCredentials, UserResponse
from app.services.auth_service import (
    DuplicateEmailError,
    authenticate_user,
    create_session_token,
    create_user,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def set_session_cookie(
    response: Response,
    user: User,
    settings: AuthSettings,
) -> None:
    """Attach the signed session token using hardened cookie attributes."""
    response.set_cookie(
        key=settings.cookie_name,
        value=create_session_token(user, settings),
        max_age=settings.token_expire_seconds,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: AuthCredentials,
    response: Response,
    session: Session = Depends(get_database_session),
    settings: AuthSettings = Depends(get_auth_settings),
) -> User:
    """Create an account and start an authenticated browser session."""
    try:
        user = create_user(session, str(payload.email), payload.password)
    except DuplicateEmailError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        ) from error

    set_session_cookie(response, user, settings)
    return user


@router.post("/login", response_model=UserResponse)
def login(
    payload: AuthCredentials,
    response: Response,
    session: Session = Depends(get_database_session),
    settings: AuthSettings = Depends(get_auth_settings),
) -> User:
    """Verify credentials and start an authenticated browser session."""
    user = authenticate_user(session, str(payload.email), payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    set_session_cookie(response, user, settings)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    settings: AuthSettings = Depends(get_auth_settings),
) -> None:
    """Clear the browser session cookie."""
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the currently authenticated account."""
    return current_user
