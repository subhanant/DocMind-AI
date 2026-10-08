"""Dashboard routes: stats and recent documents."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.database import get_db
from app.db.models.document import Document, DocumentStatus
from app.schemas.common import APIResponse
from app.schemas.notification import (
    DashboardResponse,
    DashboardStats,
    RecentDocumentItem,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/stats",
    response_model=APIResponse[DashboardStats],
    summary="Get dashboard statistics",
)
async def get_stats(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DashboardStats]:
    """
    Return real statistics from the database for the current user.
    Values are always computed from live data — never hardcoded.
    """
    user_filter = Document.user_id == current_user.id
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Total documents
    total_result = await db.execute(
        select(func.count()).select_from(Document).where(user_filter)
    )
    total_documents = total_result.scalar() or 0

    # Processed today
    processed_today_result = await db.execute(
        select(func.count())
        .select_from(Document)
        .where(
            and_(
                user_filter,
                Document.processing_status == DocumentStatus.COMPLETED,
                Document.processed_at >= today_start,
            )
        )
    )
    processed_today = processed_today_result.scalar() or 0

    # Currently processing
    processing_result = await db.execute(
        select(func.count())
        .select_from(Document)
        .where(and_(user_filter, Document.processing_status == DocumentStatus.PROCESSING))
    )
    currently_processing = processing_result.scalar() or 0

    # Needs review
    needs_review_result = await db.execute(
        select(func.count())
        .select_from(Document)
        .where(and_(user_filter, Document.processing_status == DocumentStatus.NEEDS_REVIEW))
    )
    needs_review = needs_review_result.scalar() or 0

    # Completed total
    completed_result = await db.execute(
        select(func.count())
        .select_from(Document)
        .where(and_(user_filter, Document.processing_status == DocumentStatus.COMPLETED))
    )
    total_completed = completed_result.scalar() or 0

    # Failed total
    failed_result = await db.execute(
        select(func.count())
        .select_from(Document)
        .where(and_(user_filter, Document.processing_status == DocumentStatus.FAILED))
    )
    total_failed = failed_result.scalar() or 0

    return APIResponse.ok(
        DashboardStats(
            total_documents=total_documents,
            processed_today=processed_today,
            currently_processing=currently_processing,
            needs_review=needs_review,
            total_completed=total_completed,
            total_failed=total_failed,
        )
    )


@router.get(
    "/recent-documents",
    response_model=APIResponse[list[RecentDocumentItem]],
    summary="Get recently uploaded documents",
)
async def get_recent_documents(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
) -> APIResponse[list[RecentDocumentItem]]:
    """Return the most recently uploaded documents for the current user."""
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .limit(min(limit, 50))
    )
    documents = list(result.scalars().all())

    return APIResponse.ok(
        [RecentDocumentItem.model_validate(d) for d in documents]
    )
