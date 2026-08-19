from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.auth import access
from app.auth.dependencies import CurrentUser, DbSession
from app.schemas.notification import NotificationRead
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=list[NotificationRead],
    summary="Your notifications, newest first",
)
def list_notifications(
    db: DbSession,
    current_user: CurrentUser,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[NotificationRead]:
    """The inbox is always the caller's own: there is no user filter to abuse."""
    notifications = notification_service.list_for_user(
        db,
        current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )

    return [
        NotificationRead.model_validate(notification) for notification in notifications
    ]


@router.get(
    "/unread-count",
    response_model=int,
    summary="How many of your notifications are unread",
)
def get_unread_count(db: DbSession, current_user: CurrentUser) -> int:
    return notification_service.unread_count(db, current_user.id)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
    summary="Mark one of your notifications as read",
)
def mark_notification_read(
    notification_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> NotificationRead:
    notification = notification_service.get_notification(db, notification_id)
    access.ensure_owns_notification(notification.user_id, current_user)

    return NotificationRead.model_validate(
        notification_service.mark_read(db, notification)
    )
