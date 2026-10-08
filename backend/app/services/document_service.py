"""
Document Processing Pipeline for DocuMind AI (Phase 2).

Orchestrates the 6-stage Document Intelligence Pipeline:
- Stage 1: File Validation (MIME, size, extensions, magic bytes)
- Stage 2: Storage Persistence (isolated file storage)
- Stage 3: Text Extraction & OCR Fallback (PyMuPDF native + Tesseract/Fallback OCR)
- Stage 4: AI Document Classification (Bill of Lading, Invoice, Packing list, etc.)
- Stage 5: Structured AI Extraction (Bill of Lading 27 priority fields, multiple containers)
- Stage 6: Confidence Validation, Status Assignment & Routing
"""
import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.document import Document, DocumentStatus, DocumentType, ValidationStatus
from app.schemas.extraction import ProcessingStatusResponse, ProcessingStatusStage
from app.services.ai import get_ai_provider
from app.services.schema_registry import DocumentSchemaRegistry
from app.services.storage_service import FileValidationError, StorageService, validate_file
from app.services.text_extraction_service import DocumentPagesResult, DocumentTextExtractor

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class ProcessingContext:
    """Carries complete state through all stages of the document processing pipeline."""
    user_id: uuid.UUID
    original_filename: str
    file_data: bytes
    content_type: str
    file_size: int

    # Populated as pipeline runs
    storage_path: Optional[str] = None
    validated_mime_type: Optional[str] = None
    document_id: Optional[uuid.UUID] = None
    document_type: DocumentType = DocumentType.UNKNOWN
    processing_status: DocumentStatus = DocumentStatus.QUEUED

    # Text extraction & OCR
    extracted_text: str = ""
    pages: List[dict[str, Any]] = field(default_factory=list)
    page_count: int = 1
    is_scanned: bool = False
    ocr_used: bool = False
    ocr_extractor_used: str = "pymupdf"

    # AI Classification
    classification_confidence: float = 0.0
    classification_reason: str = ""

    # Structured AI Extraction
    extraction_result: Optional[dict[str, Any]] = None
    field_evidence: Optional[dict[str, Any]] = None
    confidence_score: Optional[float] = None

    # Errors & Processing metadata
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0


# ─── Live Processing Tracker (In-Memory Progress State) ─────────────────────────

class ProcessingTracker:
    """Tracks stage-by-stage real-time progress for active documents."""

    _stages_state: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def init_document(cls, document_id: uuid.UUID, initial_status: str = "queued") -> None:
        doc_key = str(document_id)
        cls._stages_state[doc_key] = {
            "overall_status": initial_status,
            "current_stage": "validation",
            "progress_percentage": 10 if initial_status == "processing" else 5,
            "error_message": None,
            "stages": [
                {"name": "File Validation", "status": "pending", "message": "Checking file MIME, extension, and integrity"},
                {"name": "Storage Persistence", "status": "pending", "message": "Storing file securely"},
                {"name": "Text & OCR Extraction", "status": "pending", "message": "Parsing text and layout"},
                {"name": "Document Classification", "status": "pending", "message": "Classifying document type"},
                {"name": "Structured Field Extraction", "status": "pending", "message": "Extracting structured data"},
                {"name": "Confidence Validation", "status": "pending", "message": "Scoring confidence & validation"},
            ],
        }

    @classmethod
    def update_stage(
        cls,
        document_id: uuid.UUID,
        stage_name: str,
        status: str,
        message: Optional[str] = None,
        percentage: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        doc_key = str(document_id)
        if doc_key not in cls._stages_state:
            cls.init_document(document_id, "processing")

        state = cls._stages_state[doc_key]
        state["current_stage"] = stage_name
        if percentage is not None:
            state["progress_percentage"] = percentage

        for s in state["stages"]:
            if s["name"].lower() == stage_name.lower():
                s["status"] = status
                if message:
                    s["message"] = message
                if details:
                    s["details"] = details
                break

    @classmethod
    def mark_complete(cls, document_id: uuid.UUID, final_status: str = "completed") -> None:
        doc_key = str(document_id)
        if doc_key in cls._stages_state:
            state = cls._stages_state[doc_key]
            state["overall_status"] = final_status
            state["progress_percentage"] = 100
            state["current_stage"] = "Done"
            for s in state["stages"]:
                if s["status"] != "failed":
                    s["status"] = "completed"

    @classmethod
    def mark_failed(cls, document_id: uuid.UUID, error_message: str) -> None:
        doc_key = str(document_id)
        if doc_key in cls._stages_state:
            state = cls._stages_state[doc_key]
            state["overall_status"] = "failed"
            state["error_message"] = error_message
            for s in state["stages"]:
                if s["status"] == "in_progress":
                    s["status"] = "failed"

    @classmethod
    def get_status(cls, document_id: uuid.UUID, db_doc: Optional[Document] = None) -> ProcessingStatusResponse:
        doc_key = str(document_id)
        state = cls._stages_state.get(doc_key)

        if not state:
            # Reconstruct from DB model if not actively tracked in memory
            status_val = db_doc.processing_status.value if db_doc else "completed"
            is_done = status_val in {"completed", "needs_review", "failed"}
            default_stages = [
                ProcessingStatusStage(name="File Validation", status="completed" if is_done else "in_progress", message="File validated successfully"),
                ProcessingStatusStage(name="Storage Persistence", status="completed" if is_done else "pending", message="Stored in secure repository"),
                ProcessingStatusStage(name="Text & OCR Extraction", status="completed" if is_done else "pending", message="Extracted document pages"),
                ProcessingStatusStage(name="Document Classification", status="completed" if is_done else "pending", message=f"Classified as {db_doc.document_type.value if db_doc else 'document'}"),
                ProcessingStatusStage(name="Structured Field Extraction", status="completed" if is_done else "pending", message="Extracted priority fields"),
                ProcessingStatusStage(name="Confidence Validation", status="completed" if is_done else "pending", message="Validated confidence score"),
            ]
            return ProcessingStatusResponse(
                document_id=document_id,
                overall_status=status_val,
                progress_percentage=100 if is_done else 50,
                current_stage="Complete" if is_done else "Processing",
                stages=default_stages,
                error_message=None,
            )

        stages = [
            ProcessingStatusStage(
                name=s["name"],
                status=s["status"],
                message=s.get("message"),
                details=s.get("details"),
            )
            for s in state["stages"]
        ]
        return ProcessingStatusResponse(
            document_id=document_id,
            overall_status=state["overall_status"],
            progress_percentage=state["progress_percentage"],
            current_stage=state["current_stage"],
            stages=stages,
            error_message=state.get("error_message"),
        )


# ─── Stage Interfaces ─────────────────────────────────────────────────────────

class FileValidator(ABC):
    @abstractmethod
    async def validate(self, ctx: ProcessingContext) -> ProcessingContext: ...


class FileStorage(ABC):
    @abstractmethod
    async def store(self, ctx: ProcessingContext) -> ProcessingContext: ...


class TextExtractionStage(ABC):
    @abstractmethod
    async def extract_text_and_pages(self, ctx: ProcessingContext) -> ProcessingContext: ...


class DocumentClassificationStage(ABC):
    @abstractmethod
    async def classify(self, ctx: ProcessingContext) -> ProcessingContext: ...


class StructuredExtractionStage(ABC):
    @abstractmethod
    async def extract_fields(self, ctx: ProcessingContext) -> ProcessingContext: ...


class ConfidenceScoringStage(ABC):
    @abstractmethod
    async def score_and_route(self, ctx: ProcessingContext) -> ProcessingContext: ...


# ─── Concrete Stage Implementations ──────────────────────────────────────────

class StandardFileValidator(FileValidator):
    async def validate(self, ctx: ProcessingContext) -> ProcessingContext:
        if ctx.document_id:
            ProcessingTracker.update_stage(
                ctx.document_id, "File Validation", "in_progress", "Validating file MIME and size", 15
            )
        validated_mime = validate_file(
            filename=ctx.original_filename,
            content_type=ctx.content_type,
            file_size=ctx.file_size,
        )
        ctx.validated_mime_type = validated_mime
        if ctx.document_id:
            ProcessingTracker.update_stage(
                ctx.document_id, "File Validation", "completed", f"Validated MIME: {validated_mime}", 25
            )
        return ctx


class StandardFileStorage(FileStorage):
    def __init__(self, storage_service: StorageService):
        self._storage = storage_service

    async def store(self, ctx: ProcessingContext) -> ProcessingContext:
        if ctx.storage_path:
            return ctx  # Already stored

        if ctx.document_id:
            ProcessingTracker.update_stage(
                ctx.document_id, "Storage Persistence", "in_progress", "Writing file to storage", 35
            )

        storage_path = await self._storage.save(
            file_data=ctx.file_data,
            filename=ctx.original_filename,
            user_id=ctx.user_id,
            content_type=ctx.validated_mime_type or ctx.content_type,
        )
        ctx.storage_path = storage_path

        if ctx.document_id:
            ProcessingTracker.update_stage(
                ctx.document_id, "Storage Persistence", "completed", "File stored successfully", 45
            )
        return ctx


class StandardTextExtractionStage(TextExtractionStage):
    def __init__(self, extractor: Optional[DocumentTextExtractor] = None):
        self._extractor = extractor or DocumentTextExtractor()

    async def extract_text_and_pages(self, ctx: ProcessingContext) -> ProcessingContext:
        if ctx.document_id:
            ProcessingTracker.update_stage(
                ctx.document_id, "Text & OCR Extraction", "in_progress", "Extracting text and checking scanned pages", 55
            )

        mime = ctx.validated_mime_type or ctx.content_type
        pages_res: DocumentPagesResult = self._extractor.extract_pages(
            file_bytes=ctx.file_data,
            filename=ctx.original_filename,
            content_type=mime,
        )

        ctx.extracted_text = pages_res.full_text
        ctx.pages = [p.to_dict() for p in pages_res.pages]
        ctx.page_count = max(1, pages_res.total_pages)
        ctx.is_scanned = pages_res.is_scanned
        ctx.ocr_used = pages_res.ocr_used
        ctx.ocr_extractor_used = pages_res.extractor_used

        if ctx.document_id:
            msg = f"{ctx.page_count} page(s) extracted (OCR: {ctx.ocr_used})"
            ProcessingTracker.update_stage(
                ctx.document_id, "Text & OCR Extraction", "completed", msg, 65,
                details={"pages": ctx.page_count, "ocr_used": ctx.ocr_used}
            )

        return ctx


class StandardDocumentClassificationStage(DocumentClassificationStage):
    async def classify(self, ctx: ProcessingContext) -> ProcessingContext:
        if ctx.document_id:
            ProcessingTracker.update_stage(
                ctx.document_id, "Document Classification", "in_progress", "Classifying document type", 70
            )

        ai_provider = get_ai_provider()
        # Pass image_bytes for scanned/photo documents so Gemini can classify from image
        is_image = (ctx.validated_mime_type or ctx.content_type or "").startswith("image/")
        meta: dict[str, Any] = {"filename": ctx.original_filename, "size": ctx.file_size}
        if is_image or ctx.is_scanned:
            meta["image_bytes"] = ctx.file_data
        classification = await ai_provider.classify_document(
            text=ctx.extracted_text,
            pages=ctx.pages,
            metadata=meta,
        )

        # Match to DocumentType enum
        try:
            doc_type = DocumentType(classification.document_type)
        except ValueError:
            doc_type = DocumentType.UNKNOWN

        ctx.document_type = doc_type
        ctx.classification_confidence = classification.confidence
        ctx.classification_reason = classification.reason

        if ctx.document_id:
            msg = f"Detected: {doc_type.value} ({int(classification.confidence * 100)}%)"
            ProcessingTracker.update_stage(
                ctx.document_id, "Document Classification", "completed", msg, 80,
                details={"document_type": doc_type.value, "confidence": classification.confidence}
            )

        return ctx


class StandardStructuredExtractionStage(StructuredExtractionStage):
    async def extract_fields(self, ctx: ProcessingContext) -> ProcessingContext:
        if ctx.document_id:
            ProcessingTracker.update_stage(
                ctx.document_id, "Structured Field Extraction", "in_progress", "Extracting document schema fields", 85
            )

        ai_provider = get_ai_provider()

        # Pass image_bytes for scanned/photo documents so Gemini can extract directly from image
        is_image = (ctx.validated_mime_type or ctx.content_type or "").startswith("image/")
        extract_meta: dict[str, Any] = {"filename": ctx.original_filename}
        if is_image or ctx.is_scanned:
            extract_meta["image_bytes"] = ctx.file_data

        # Check if schema is implemented for this document type
        if ctx.document_type == DocumentType.BILL_OF_LADING:
            try:
                from app.services.vision import DocumentVisionPipeline
                vision_pipeline = DocumentVisionPipeline()
                mime = ctx.validated_mime_type or ctx.content_type or "application/pdf"
                vision_output = await vision_pipeline.process_document(
                    file_bytes=ctx.file_data,
                    mime_type=mime,
                    filename=ctx.original_filename,
                    document_id=str(ctx.document_id) if ctx.document_id else None,
                )
                ctx.extraction_result = vision_output.extracted_data
                ctx.field_evidence = vision_output.field_evidence
                ctx.confidence_score = vision_output.overall_confidence
            except Exception as e:
                logger.error("Document vision pipeline failed, falling back to legacy extractor", error=str(e), exc_info=True)
                data, evidence, confidence = await ai_provider.extract_bill_of_lading(
                    text=ctx.extracted_text,
                    pages=ctx.pages,
                    metadata=extract_meta,
                )
                ctx.extraction_result = data
                ctx.field_evidence = evidence
                ctx.confidence_score = confidence
        else:
            # Other document types: classification works, report unimplemented schema
            unimpl_msg = DocumentSchemaRegistry.get_unimplemented_message(ctx.document_type.value)
            ctx.extraction_result = {
                "document_type": ctx.document_type.value,
                "status": "unimplemented",
                "message": unimpl_msg,
            }
            ctx.field_evidence = {}
            ctx.confidence_score = 0.50

        if ctx.document_id:
            ProcessingTracker.update_stage(
                ctx.document_id, "Structured Field Extraction", "completed", "Field extraction completed", 90
            )

        return ctx


class StandardConfidenceScoringStage(ConfidenceScoringStage):
    async def score_and_route(self, ctx: ProcessingContext) -> ProcessingContext:
        if ctx.document_id:
            ProcessingTracker.update_stage(
                ctx.document_id, "Confidence Validation", "in_progress", "Evaluating confidence score", 95
            )

        score = ctx.confidence_score or 0.0
        threshold = settings.EXTRACTION_CONFIDENCE_THRESHOLD

        if ctx.errors:
            ctx.processing_status = DocumentStatus.FAILED
        elif ctx.document_type == DocumentType.UNKNOWN:
            ctx.processing_status = DocumentStatus.NEEDS_REVIEW
        elif score >= threshold and ctx.extraction_result:
            ctx.processing_status = DocumentStatus.COMPLETED
        elif score > 0.0 and ctx.extraction_result:
            ctx.processing_status = DocumentStatus.NEEDS_REVIEW
        else:
            ctx.processing_status = DocumentStatus.NEEDS_REVIEW

        if ctx.document_id:
            ProcessingTracker.update_stage(
                ctx.document_id, "Confidence Validation", "completed", f"Status routed: {ctx.processing_status.value}", 100
            )
            ProcessingTracker.mark_complete(ctx.document_id, ctx.processing_status.value)

        return ctx


# ─── Full Pipeline Orchestrator ──────────────────────────────────────────────

class DocumentProcessor:
    """Orchestrates end-to-end document processing pipeline."""

    def __init__(
        self,
        validator: FileValidator,
        storage: FileStorage,
        text_extractor: TextExtractionStage,
        classifier: DocumentClassificationStage,
        extractor: StructuredExtractionStage,
        confidence_engine: ConfidenceScoringStage,
    ):
        self._validator = validator
        self._storage = storage
        self._text_extractor = text_extractor
        self._classifier = classifier
        self._extractor = extractor
        self._confidence_engine = confidence_engine

    async def process(self, ctx: ProcessingContext) -> ProcessingContext:
        start_time = time.time()
        try:
            # 1. Validation
            ctx = await self._validator.validate(ctx)

            # 2. Storage
            ctx = await self._storage.store(ctx)

            # 3. Text & OCR Extraction
            ctx = await self._text_extractor.extract_text_and_pages(ctx)

            # 4. Document Classification
            ctx = await self._classifier.classify(ctx)

            # 5. Structured AI Extraction
            ctx = await self._extractor.extract_fields(ctx)

            # 6. Confidence Scoring & Routing
            ctx = await self._confidence_engine.score_and_route(ctx)

            ctx.duration_seconds = round(time.time() - start_time, 2)
            logger.info(
                "Document processing pipeline complete",
                filename=ctx.original_filename,
                document_type=ctx.document_type.value,
                status=ctx.processing_status.value,
                confidence=ctx.confidence_score,
                duration=ctx.duration_seconds,
            )

        except FileValidationError as e:
            ctx.processing_status = DocumentStatus.FAILED
            ctx.errors.append(str(e))
            if ctx.document_id:
                ProcessingTracker.mark_failed(ctx.document_id, str(e))
            logger.warning("File validation failed", filename=ctx.original_filename, error=str(e))
            raise

        except Exception as e:
            ctx.processing_status = DocumentStatus.FAILED
            ctx.errors.append(str(e))
            if ctx.document_id:
                ProcessingTracker.mark_failed(ctx.document_id, str(e))
            logger.error("Document processing pipeline failed", filename=ctx.original_filename, error=str(e))
            raise

        return ctx


def build_document_processor(storage_service: StorageService) -> DocumentProcessor:
    """Builds and returns the full production document processor instance."""
    return DocumentProcessor(
        validator=StandardFileValidator(),
        storage=StandardFileStorage(storage_service),
        text_extractor=StandardTextExtractionStage(),
        classifier=StandardDocumentClassificationStage(),
        extractor=StandardStructuredExtractionStage(),
        confidence_engine=StandardConfidenceScoringStage(),
    )
