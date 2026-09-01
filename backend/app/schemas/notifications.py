"""Response schemas for authenticated in-app notifications."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    """User-visible notification data without persistence internals."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime


class UnreadNotificationCountResponse(BaseModel):
    """Current unread notification total."""

    unread_count: int


class MarkAllNotificationsReadResponse(BaseModel):
    """Number of notifications changed by a mark-all operation."""

    updated_count: int
