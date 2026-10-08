"""
Notification Service.

Phase 1: Creates in-database notifications synchronously.
Phase 9+: Replace with async WebSocket/SSE broadcast using Redis pub/sub.
"""
import uuid
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.document import Document, DocumentStatus, DocumentType, Notification, NotificationType

logger = get_logger(__name__)


class NotificationService:
    """
    Creates and manages user notifications.
    
    Phase 1: Synchronous database notifications only.
    Phase 9+: Add WebSocket/SSE real-time broadcasting via Redis pub/sub.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_upload_notification(
        self,
        user_id: uuid.UUID,
        document: Document,
    ) -> Notification:
        """Create a notification when a document is successfully uploaded."""
        notification = Notification(
            user_id=user_id,
            document_id=document.id,
            type=NotificationType.UPLOAD_COMPLETE,
            title="Document uploaded successfully",
            message=f"'{document.original_filename}' has been uploaded and queued for processing.",
            is_read=False,
        )
        self._db.add(notification)
        await self._db.flush()
        logger.info(
            "Upload notification created",
            user_id=str(user_id),
            document_id=str(document.id),
        )
        return notification

    async def create_processing_complete_notification(
        self,
        user_id: uuid.UUID,
        document: Document,
        confidence: Optional[float] = None,
        custom_message: Optional[str] = None,
    ) -> Notification:
        """Create a notification when document processing completes."""
        type_name = "Bill of Lading" if document.document_type == DocumentType.BILL_OF_LADING else document.document_type.value.replace("_", " ").title()
        msg = custom_message or f"{type_name} extraction completed."
        notification = Notification(
            user_id=user_id,
            document_id=document.id,
            type=NotificationType.PROCESSING_COMPLETE,
            title="Document extracted successfully",
            message=msg,
            is_read=False,
        )
        self._db.add(notification)
        await self._db.flush()
        return notification

    async def create_failed_notification(
        self,
        user_id: uuid.UUID,
        document: Document,
        reason: Optional[str] = None,
    ) -> Notification:
        """Create a notification when document processing fails."""
        notification = Notification(
            user_id=user_id,
            document_id=document.id,
            type=NotificationType.PROCESSING_FAILED,
            title="Document extraction failed",
            message="We could not extract this document. Please review or retry.",
            is_read=False,
        )
        self._db.add(notification)
        await self._db.flush()
        return notification

    async def create_needs_review_notification(
        self,
        user_id: uuid.UUID,
        document: Document,
    ) -> Notification:
        """Create a notification when a document requires human review."""
        notification = Notification(
            user_id=user_id,
            document_id=document.id,
            type=NotificationType.NEEDS_REVIEW,
            title="Document requires review",
            message="Some extracted fields have low confidence.",
            is_read=False,
        )
        self._db.add(notification)
        await self._db.flush()
        return notification

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> list[Notification]:
        """Retrieve one page of notifications for a user, newest first."""
        query = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        if unread_only:
            query = query.where(Notification.is_read == False)  # noqa: E712

        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def get_notification_count(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
    ) -> int:
        """Count notifications matching the current list filter."""
        query = select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)  # noqa: E712
        result = await self._db.execute(query)
        return result.scalar() or 0

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Count unread notifications for a user."""
        result = await self._db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
        )
        return result.scalar() or 0

    async def mark_as_read(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Notification]:
        """Mark a single notification as read."""
        result = await self._db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.is_read = True
            await self._db.flush()
        return notification

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """Mark all notifications as read for a user. Returns count updated."""
        result = await self._db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
            .values(is_read=True)
        )
        return result.rowcount

    # Phase 9+: Add WebSocket broadcast methods here
    # async def broadcast_to_user(self, user_id: uuid.UUID, event: dict) -> None:
    #     """Broadcast real-time event via Redis pub/sub."""
    #     ...
