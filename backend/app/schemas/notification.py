"""Pydantic schemas for notifications and dashboard."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.db.models.document import NotificationType, DocumentType, DocumentStatus


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    document_id: Optional[uuid.UUID]
    type: NotificationType
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
    total: int
    page: int
    size: int
    pages: int


class DashboardStats(BaseModel):
    total_documents: int
    processed_today: int
    currently_processing: int
    needs_review: int
    total_completed: int
    total_failed: int


class RecentDocumentItem(BaseModel):
    id: uuid.UUID
    original_filename: str
    document_type: DocumentType
    processing_status: DocumentStatus
    extraction_confidence: Optional[float]
    uploaded_at: datetime
    file_size: int

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_documents: list[RecentDocumentItem]
