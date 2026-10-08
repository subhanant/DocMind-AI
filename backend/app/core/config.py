"""
Application configuration.
All settings are loaded from environment variables or .env file.
"""
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "DocuMind AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered document intelligence platform"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ─── Security ────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    JWT_SECRET: str = "change-me-jwt-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ─── CORS ───────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # ─── Database ────────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://documind:documind@localhost:5432/documind"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ─── Redis ───────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ─── File Storage ────────────────────────────────────────────────────────────
    STORAGE_BACKEND: str = "local"  # local | s3 | gcs | azure
    STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "jpg", "jpeg", "png", "webp", "docx", "xlsx"]
    ALLOWED_MIME_TYPES: List[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]

    # ─── AI Extraction & OCR (Phase 2) ──────────────────────────────────────────
    GEMINI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gemini-flash-lite-latest"
    AI_REQUEST_TIMEOUT: int = 30
    OCR_ENABLED: bool = True
    OCR_LANGUAGE: str = "eng"
    OCR_MIN_CHARS_THRESHOLD: int = 50
    EXTRACTION_CONFIDENCE_THRESHOLD: float = 0.75

    # ─── Future: OAuth (Phase 6+) ────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None

    # ─── Legacy / Alternate AI settings ─────────────────────────────────────────
    AI_API_KEY: Optional[str] = None
    AI_MAX_TOKENS: int = 4096

    # ─── Future: Storage (Phase 10+) ─────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None

    @field_validator("MAX_UPLOAD_SIZE_MB")
    @classmethod
    def validate_upload_size(cls, v: int) -> int:
        if v <= 0 or v > 500:
            raise ValueError("MAX_UPLOAD_SIZE_MB must be between 1 and 500")
        return v

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug_value(cls, v: Any) -> Any:
        """Accept common deployment labels supplied by Windows environments."""
        if isinstance(v, str):
            value = v.strip().lower()
            if value in {"release", "production", "prod"}:
                return False
            if value in {"development", "dev", "debug"}:
                return True
        return v

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def storage_path_resolved(self) -> Path:
        return Path(self.STORAGE_PATH).resolve()


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
