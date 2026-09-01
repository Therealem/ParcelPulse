"""Authenticated, owner-scoped in-app notification routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.config import ApplicationSettings, get_application_settings
from app.database import get_database_session
from app.models import User
from app.schemas.notifications import (
    MarkAllNotificationsReadResponse,
    NotificationResponse,
    UnreadNotificationCountResponse,
)
from app.services.notification_service import (
    NotificationPersistenceError,
    create_development_test_notification,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    unread_notification_count,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _notification_service_error(
    error: NotificationPersistenceError,
) -> HTTPException:
    logger.error("Notification operation failed: %s", type(error).__name__)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Notifications are temporarily unavailable",
    )


def _require_development_notification_endpoint(
    settings: ApplicationSettings,
) -> None:
    """Hide development controls unless both safety gates are active."""
    if (
        settings.app_environment != "development"
        or not settings.enable_dev_notification_endpoint
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )


@router.get("/dev/status", include_in_schema=False)
def read_test_notification_status(
    current_user: User = Depends(get_current_user),
    settings: ApplicationSettings = Depends(get_application_settings),
) -> dict[str, bool]:
    """Advertise the test control only to an authenticated local user."""
    _require_development_notification_endpoint(settings)
    return {"enabled": True}


@router.post(
    "/dev/test",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_test_notification(
    session: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
    settings: ApplicationSettings = Depends(get_application_settings),
) -> NotificationResponse:
    """Create one authenticated local test alert when explicitly enabled."""
    _require_development_notification_endpoint(settings)
    try:
        notification = create_development_test_notification(
            session,
            current_user.id,
        )
    except NotificationPersistenceError as error:
        raise _notification_service_error(error) from error
    return NotificationResponse.model_validate(notification)


@router.get("", response_model=list[NotificationResponse])
def read_notifications(
    session: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> list[NotificationResponse]:
    """Return the authenticated user's notifications, newest first."""
    try:
        notifications = list_notifications(session, current_user.id)
    except NotificationPersistenceError as error:
        raise _notification_service_error(error) from error
    return [
        NotificationResponse.model_validate(notification)
        for notification in notifications
    ]


@router.get(
    "/unread-count",
    response_model=UnreadNotificationCountResponse,
)
def read_unread_notification_count(
    session: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> UnreadNotificationCountResponse:
    """Return the authenticated user's unread notification count."""
    try:
        count = unread_notification_count(session, current_user.id)
    except NotificationPersistenceError as error:
        raise _notification_service_error(error) from error
    return UnreadNotificationCountResponse(unread_count=count)


@router.patch(
    "/read-all",
    response_model=MarkAllNotificationsReadResponse,
)
def read_all_notifications(
    session: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> MarkAllNotificationsReadResponse:
    """Mark all of the authenticated user's current notifications read."""
    try:
        count = mark_all_notifications_read(session, current_user.id)
    except NotificationPersistenceError as error:
        raise _notification_service_error(error) from error
    return MarkAllNotificationsReadResponse(updated_count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def read_one_notification(
    notification_id: int,
    session: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    """Mark one owned notification read without revealing other records."""
    try:
        notification = mark_notification_read(
            session,
            notification_id,
            current_user.id,
        )
    except NotificationPersistenceError as error:
        raise _notification_service_error(error) from error
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return NotificationResponse.model_validate(notification)
