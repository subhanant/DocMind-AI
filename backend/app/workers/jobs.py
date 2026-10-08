"""
Background job definitions.

Phase 1: Job abstractions only (no real queue yet).
Phase 2+: Connect to Celery/Redis for async document processing.

The job interface is defined here so it can be wired into a real
task queue without changing the rest of the codebase.
"""
from typing import Any
from app.core.logging import get_logger

logger = get_logger(__name__)


class JobQueue:
    """
    Abstract job queue interface.
    
    Phase 1: Synchronous in-process execution (noop for most jobs).
    Phase 2+: Replace with Celery + Redis for async background processing.
    """

    async def enqueue_document_processing(
        self,
        document_id: str,
        user_id: str,
        priority: int = 5,
    ) -> str:
        """
        Enqueue a document for async processing.
        
        Phase 1: No-op — documents are handled synchronously during upload.
        Phase 2+: Push to Celery task queue.
        
        Returns a job ID for tracking.
        """
        logger.info(
            "Document processing enqueued (Phase 1: synchronous)",
            document_id=document_id,
            user_id=user_id,
        )
        return f"sync-{document_id}"

    async def enqueue_email_processing(
        self,
        connection_id: str,
        user_id: str,
    ) -> str:
        """
        Phase 8+: Enqueue email attachment processing.
        Triggered by Gmail/Outlook webhook or scheduled poll.
        """
        raise NotImplementedError("Email processing is a Phase 8 feature.")

    async def get_job_status(self, job_id: str) -> dict[str, Any]:
        """
        Get the current status of a background job.
        Phase 2+: Query Celery task state from Redis.
        """
        return {"job_id": job_id, "status": "completed", "phase": 1}


# Singleton instance
job_queue = JobQueue()


# ─── Future Celery Task Definitions (Phase 2+) ───────────────────────────────
# from celery import Celery
# from app.core.config import get_settings
#
# settings = get_settings()
# celery_app = Celery(
#     "documind",
#     broker=settings.CELERY_BROKER_URL,
#     backend=settings.CELERY_RESULT_BACKEND,
# )
#
# @celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
# def process_document_task(self, document_id: str, user_id: str):
#     """Async document processing task."""
#     ...
