"""
Pydantic schemas for document endpoints.
Covers upload, listing, details, and deletion responses.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.db.models.document import DocumentStatus, DocumentType


class DocumentResponse(BaseModel):
    """Full document representation returned by the API."""
    id: uuid.UUID
    user_id: uuid.UUID
    original_filename: str
    file_type: str
    mime_type: str
    file_size: int
    document_type: DocumentType
    processing_status: DocumentStatus
    extraction_confidence: Optional[float]
    uploaded_at: datetime
    processed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    items: list[DocumentResponse]
    total: int
    page: int
    size: int = 20
    pages: int = 1
    page_size: Optional[int] = None
    total_pages: Optional[int] = None

    def model_post_init(self, __context: Any) -> None:
        if self.page_size is None:
            self.page_size = self.size
        if self.total_pages is None:
            self.total_pages = self.pages


class DocumentUploadResponse(BaseModel):
    """Response after a successful document upload."""
    document: DocumentResponse
    message: str = "Document uploaded successfully. Processing has been queued."


class DocumentDeleteResponse(BaseModel):
    message: str = "Document deleted successfully."


class DocumentFilterParams(BaseModel):
    """Query parameters for document listing with search & filtering."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    document_type: Optional[DocumentType] = None
    processing_status: Optional[DocumentStatus] = None
    search: Optional[str] = Field(default=None, max_length=255)
    sort_by: str = Field(default="uploaded_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
