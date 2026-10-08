"""Health check endpoint."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.database import get_db
from app.schemas.common import APIResponse

settings = get_settings()
router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=APIResponse[dict],
    summary="Health check",
)
async def health_check(db: AsyncSession = Depends(get_db)) -> APIResponse[dict]:
    """
    Returns application health status including database connectivity.
    Used by Docker health checks and monitoring systems.
    """
    db_status = "ok"
    db_error = None

    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "error"
        db_error = "Database connection failed"

    return APIResponse.ok({
        "status": "ok" if db_status == "ok" else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": db_status,
        },
        **({"errors": {"database": db_error}} if db_error else {}),
    })
