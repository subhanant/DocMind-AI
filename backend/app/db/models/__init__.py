"""Models package — imports all models so Alembic can discover them."""
from app.db.models.document import (  # noqa: F401
    Document,
    DocumentStatus,
    DocumentType,
    EmailConnection,
    EmailProvider,
    ExtractionResult,
    Notification,
    NotificationType,
    ValidationStatus,
)
from app.db.models.user import User, UserRole  # noqa: F401

__all__ = [
    "User",
    "UserRole",
    "Document",
    "DocumentStatus",
    "DocumentType",
    "ExtractionResult",
    "ValidationStatus",
    "Notification",
    "NotificationType",
    "EmailConnection",
    "EmailProvider",
]
