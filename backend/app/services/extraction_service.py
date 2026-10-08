"""
Extraction Service.

Manages saving, retrieving, updating, and auditing structured extraction results.
Preserves audit history for field edits as specified in Phase 2 Section 21.
"""
import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.document import Document, DocumentStatus, ExtractionResult, ValidationStatus
from app.schemas.extraction import ExtractionResultDetail

logger = get_logger(__name__)


class ExtractionService:
    """Manages structured extraction records in database."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def save_extraction_result(
        self,
        document_id: uuid.UUID,
        extracted_json: Optional[Dict[str, Any]],
        confidence_score: Optional[float] = None,
        validation_status: ValidationStatus = ValidationStatus.PENDING,
        field_evidence: Optional[Dict[str, Any]] = None,
        processing_metadata: Optional[Dict[str, Any]] = None,
        schema_version: str = "2.0",
    ) -> ExtractionResult:
        """Create or update extraction result with provenance and metadata."""
        payload = copy.deepcopy(extracted_json) if extracted_json else {}

        if field_evidence and "field_evidence" not in payload:
            payload["field_evidence"] = field_evidence
        if processing_metadata and "processing_metadata" not in payload:
            payload["processing_metadata"] = processing_metadata
        if "__original_extraction" not in payload and extracted_json:
            payload["__original_extraction"] = copy.deepcopy(extracted_json)
        if "edit_history" not in payload:
            payload["edit_history"] = []

        existing = await self.get_by_document_id(document_id)
        if existing:
            existing.extracted_json = payload
            existing.confidence_score = confidence_score
            existing.validation_status = validation_status
            existing.schema_version = schema_version
            await self._db.flush()
            await self._db.refresh(existing)
            logger.info("Extraction result updated", document_id=str(document_id), confidence=confidence_score)
            return existing

        result = ExtractionResult(
            document_id=document_id,
            schema_version=schema_version,
            extracted_json=payload,
            confidence_score=confidence_score,
            validation_status=validation_status,
        )
        self._db.add(result)
        await self._db.flush()
        await self._db.refresh(result)
        logger.info("Extraction result saved", document_id=str(document_id), confidence=confidence_score)
        return result

    async def create_empty_result(self, document_id: uuid.UUID) -> ExtractionResult:
        """Create empty placeholder."""
        return await self.save_extraction_result(
            document_id=document_id,
            extracted_json=None,
            confidence_score=None,
            validation_status=ValidationStatus.PENDING,
        )

    async def get_by_document_id(self, document_id: uuid.UUID) -> Optional[ExtractionResult]:
        """Get the most recent extraction result for a document."""
        result = await self._db.execute(
            select(ExtractionResult)
            .where(ExtractionResult.document_id == document_id)
            .order_by(ExtractionResult.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_extracted_json(
        self,
        document_id: uuid.UUID,
        updated_data: Dict[str, Any],
        user_identifier: Optional[str] = "user",
        validation_status: ValidationStatus = ValidationStatus.VALID,
    ) -> Optional[ExtractionResult]:
        """
        Update extraction JSON with edited or human-validated data.
        Maintains audit log of original vs edited values.
        """
        result = await self.get_by_document_id(document_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        if not result:
            payload = copy.deepcopy(updated_data)
            payload["edit_history"] = [{
                "field_path": "all",
                "original_value": None,
                "edited_value": updated_data,
                "edited_by": user_identifier,
                "edited_at": now_iso,
            }]
            payload["__original_extraction"] = copy.deepcopy(updated_data)
            result = await self.save_extraction_result(
                document_id=document_id,
                extracted_json=payload,
                confidence_score=1.0,
                validation_status=validation_status,
            )
        else:
            current_payload = result.extracted_json or {}
            original = current_payload.get("__original_extraction") or copy.deepcopy(current_payload)
            history = current_payload.get("edit_history") or []

            # Record edit history entry
            history.append({
                "field_path": "manual_edit",
                "original_value": copy.deepcopy(current_payload),
                "edited_value": copy.deepcopy(updated_data),
                "edited_by": user_identifier,
                "edited_at": now_iso,
            })

            new_payload = copy.deepcopy(updated_data)
            new_payload["__original_extraction"] = original
            new_payload["edit_history"] = history
            if "field_evidence" in current_payload and "field_evidence" not in new_payload:
                new_payload["field_evidence"] = current_payload["field_evidence"]
            if "processing_metadata" in current_payload and "processing_metadata" not in new_payload:
                new_payload["processing_metadata"] = current_payload["processing_metadata"]

            result.extracted_json = new_payload
            result.validation_status = validation_status
            await self._db.flush()
            await self._db.refresh(result)

        # Update Document status to COMPLETED
        doc_res = await self._db.execute(select(Document).where(Document.id == document_id))
        doc = doc_res.scalar_one_or_none()
        if doc:
            doc.processing_status = DocumentStatus.COMPLETED
            await self._db.flush()

        logger.info("Extraction result updated with audit record", document_id=str(document_id), user=user_identifier)
        return result

    def format_detail(self, result: Optional[ExtractionResult]) -> ExtractionResultDetail:
        """Format an ExtractionResult into an ExtractionResultDetail for API response."""
        now = datetime.now(timezone.utc)
        if not result:
            return ExtractionResultDetail(
                id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                schema_version="2.0",
                extracted_json=None,
                confidence_score=None,
                validation_status=ValidationStatus.PENDING,
                field_evidence=None,
                edit_history=[],
                processing_metadata=None,
                created_at=now,
                updated_at=now,
            )

        data = result.extracted_json or {}
        field_evidence = data.get("field_evidence")
        edit_history = data.get("edit_history", [])
        processing_metadata = data.get("processing_metadata")

        # Strip internal keys from user-facing extracted_json view
        user_facing_json = {
            k: v for k, v in data.items()
            if not k.startswith("__") and k not in {"field_evidence", "edit_history", "processing_metadata"}
        }

        return ExtractionResultDetail(
            id=result.id,
            document_id=result.document_id,
            schema_version=result.schema_version,
            extracted_json=user_facing_json or None,
            confidence_score=result.confidence_score,
            validation_status=result.validation_status,
            field_evidence=field_evidence,
            edit_history=edit_history,
            processing_metadata=processing_metadata,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
