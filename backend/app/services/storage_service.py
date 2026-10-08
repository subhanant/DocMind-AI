"""
Storage Service abstraction.

Phase 1: LocalStorageService — stores files on disk.
Phase 10+: Implement S3StorageService, GCSStorageService, AzureStorageService.

The abstract interface ensures the rest of the codebase
can switch storage backends without changing any business logic.
"""
import hashlib
import mimetypes
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional

import aiofiles
import aiofiles.os

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Mimetypes that are allowed regardless of system detection
FALLBACK_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class FileValidationError(StorageError):
    """Raised when a file fails validation."""
    code: str

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


class StorageService(ABC):
    """
    Abstract base class for file storage.
    
    All storage backends must implement these methods.
    This abstraction allows seamless switching between
    local disk, S3, GCS, Azure, or MinIO in the future.
    """

    @abstractmethod
    async def save(
        self,
        file_data: bytes,
        filename: str,
        user_id: uuid.UUID,
        content_type: str,
    ) -> str:
        """
        Save a file and return its storage path/key.
        The returned path is an opaque identifier used for retrieval.
        """
        ...

    @abstractmethod
    async def get(self, storage_path: str) -> bytes:
        """Retrieve file contents by storage path/key."""
        ...

    @abstractmethod
    async def delete(self, storage_path: str) -> None:
        """Delete a file by storage path/key."""
        ...

    @abstractmethod
    async def get_url(self, storage_path: str) -> str:
        """Return a URL/path for accessing the file."""
        ...


class LocalStorageService(StorageService):
    """
    Local filesystem storage for development.
    
    Files are organised as:
        {storage_root}/{user_id}/{year}/{month}/{safe_filename}
    
    This structure supports future migration to S3-compatible paths.
    """

    def __init__(self, storage_root: Optional[Path] = None):
        self.storage_root = storage_root or settings.storage_path_resolved
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def _get_user_dir(self, user_id: uuid.UUID) -> Path:
        """Return the user's storage directory, creating it if needed."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        user_dir = self.storage_root / str(user_id) / str(now.year) / f"{now.month:02d}"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _generate_safe_filename(self, original_filename: str) -> str:
        """
        Generate a safe, unique filename.
        NEVER trust the original filename — it may contain path traversal attacks.
        """
        suffix = Path(original_filename).suffix.lower()
        unique_id = uuid.uuid4().hex
        return f"{unique_id}{suffix}"

    async def save(
        self,
        file_data: bytes,
        filename: str,
        user_id: uuid.UUID,
        content_type: str,
    ) -> str:
        """Save file to local disk. Returns relative storage path."""
        user_dir = self._get_user_dir(user_id)
        safe_filename = self._generate_safe_filename(filename)
        file_path = user_dir / safe_filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_data)

        # Return path relative to storage root for portability
        rel_path = file_path.relative_to(self.storage_root)
        storage_path = str(rel_path).replace("\\", "/")

        logger.info(
            "File saved",
            user_id=str(user_id),
            original_filename=filename,
            storage_path=storage_path,
            size_bytes=len(file_data),
        )
        return storage_path

    async def get(self, storage_path: str) -> bytes:
        """Read file from local disk."""
        # Security: resolve path and ensure it stays within storage root
        file_path = (self.storage_root / storage_path).resolve()
        if not str(file_path).startswith(str(self.storage_root)):
            raise StorageError("Path traversal detected")

        if not file_path.exists():
            raise StorageError(f"File not found: {storage_path}")

        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def delete(self, storage_path: str) -> None:
        """Delete file from local disk."""
        file_path = (self.storage_root / storage_path).resolve()
        if not str(file_path).startswith(str(self.storage_root)):
            raise StorageError("Path traversal detected")

        if file_path.exists():
            await aiofiles.os.remove(file_path)
            logger.info("File deleted", storage_path=storage_path)

    async def get_url(self, storage_path: str) -> str:
        """Return local file path as URL (dev only)."""
        return f"/api/documents/file/{storage_path}"


# ─── Phase 10+ Stubs ─────────────────────────────────────────────────────────

class S3StorageService(StorageService):
    """
    AWS S3 storage backend.
    Phase 10+: Implement using boto3/aiobotocore.
    """

    async def save(self, file_data: bytes, filename: str, user_id: uuid.UUID, content_type: str) -> str:
        raise NotImplementedError("S3 storage not implemented in Phase 1")

    async def get(self, storage_path: str) -> bytes:
        raise NotImplementedError("S3 storage not implemented in Phase 1")

    async def delete(self, storage_path: str) -> None:
        raise NotImplementedError("S3 storage not implemented in Phase 1")

    async def get_url(self, storage_path: str) -> str:
        raise NotImplementedError("S3 storage not implemented in Phase 1")


class GCSStorageService(StorageService):
    """
    Google Cloud Storage backend.
    Phase 10+: Implement using google-cloud-storage.
    """

    async def save(self, file_data: bytes, filename: str, user_id: uuid.UUID, content_type: str) -> str:
        raise NotImplementedError("GCS storage not implemented in Phase 1")

    async def get(self, storage_path: str) -> bytes:
        raise NotImplementedError("GCS storage not implemented in Phase 1")

    async def delete(self, storage_path: str) -> None:
        raise NotImplementedError("GCS storage not implemented in Phase 1")

    async def get_url(self, storage_path: str) -> str:
        raise NotImplementedError("GCS storage not implemented in Phase 1")


def get_storage_service() -> StorageService:
    """
    Factory function that returns the configured storage backend.
    Change STORAGE_BACKEND env variable to switch backends.
    """
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "local":
        return LocalStorageService()
    elif backend == "s3":
        return S3StorageService()
    elif backend == "gcs":
        return GCSStorageService()
    else:
        raise ValueError(f"Unknown storage backend: {backend}")


def validate_file(
    filename: str,
    content_type: str,
    file_size: int,
) -> str:
    """
    Validate file before storage.
    
    Returns the detected/validated MIME type.
    Raises FileValidationError on any violation.
    
    Security checks:
    - Extension whitelist
    - MIME type whitelist
    - File size limit
    - Filename sanitization
    """
    # Check file size
    if file_size > settings.max_upload_size_bytes:
        raise FileValidationError(
            f"File size {file_size / (1024*1024):.1f}MB exceeds maximum "
            f"{settings.MAX_UPLOAD_SIZE_MB}MB.",
            code="FILE_TOO_LARGE",
        )

    if file_size == 0:
        raise FileValidationError("File is empty.", code="EMPTY_FILE")

    # Check extension
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix not in settings.ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"File type '.{suffix}' is not supported. "
            f"Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}",
            code="INVALID_FILE_TYPE",
        )

    # Check MIME type
    # Note: We trust the suffix-based MIME type as a fallback.
    # Phase 2+: Use python-magic to verify actual file content (magic bytes).
    ext_key = f".{suffix}"
    expected_mime = FALLBACK_MIME_TYPES.get(ext_key)
    if expected_mime and content_type not in settings.ALLOWED_MIME_TYPES:
        # Gracefully handle when browser sends octet-stream
        if content_type != "application/octet-stream":
            raise FileValidationError(
                f"MIME type '{content_type}' is not supported.",
                code="INVALID_MIME_TYPE",
            )

    return expected_mime or content_type
