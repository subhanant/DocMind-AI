"""Notification routes."""
import uuid
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.database import get_db
from app.schemas.common import APIResponse
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=APIResponse[NotificationListResponse],
    summary="List notifications for the current user",
)
async def list_notifications(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=50, ge=1, le=100, description="Items per page"),
) -> APIResponse[NotificationListResponse]:
    """Return paginated notifications for the current user."""
    service = NotificationService(db)
    notifications = await service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        page=page,
        size=size,
    )
    total = await service.get_notification_count(current_user.id, unread_only=unread_only)
    unread_count = await service.get_unread_count(current_user.id)

    return APIResponse.ok(
        NotificationListResponse(
            items=[NotificationResponse.model_validate(n) for n in notifications],
            unread_count=unread_count,
            total=total,
            page=page,
            size=size,
            pages=ceil(total / size) if total else 0,
        )
    )


@router.patch(
    "/{notification_id}/read",
    response_model=APIResponse[NotificationResponse],
    summary="Mark a notification as read",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[NotificationResponse]:
    """Mark a specific notification as read."""
    service = NotificationService(db)
    notification = await service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    return APIResponse.ok(NotificationResponse.model_validate(notification))


@router.patch(
    "/read-all",
    response_model=APIResponse[dict],
    summary="Mark all notifications as read",
)
async def mark_all_read(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Mark all notifications as read for the current user."""
    service = NotificationService(db)
    count = await service.mark_all_read(current_user.id)
    return APIResponse.ok({"marked_read": count, "message": f"Marked {count} notification(s) as read."})
