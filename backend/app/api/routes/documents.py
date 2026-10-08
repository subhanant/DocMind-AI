"""
Document routes: upload, list, get, delete, extraction, reprocess, text, processing-status, file streaming.
Phase 2: Complete OCR & AI Extraction Pipeline integration.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import AsyncSessionLocal, get_db
from app.db.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    ExtractionResult,
    ValidationStatus,
)
from app.schemas.common import APIResponse
from app.schemas.document import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.schemas.extraction import (
    DocumentTextResponse,
    ExtractionResultDetail,
    ProcessingStatusResponse,
)
from app.services.document_service import (
    ProcessingContext,
    ProcessingTracker,
    build_document_processor,
)
from app.services.extraction_service import ExtractionService
from app.services.notification_service import NotificationService
from app.services.storage_service import (
    FileValidationError,
    get_storage_service,
    validate_file,
)
from app.services import ai as ai_services

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


async def execute_pipeline_for_document(
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    session: Optional[AsyncSession] = None,
) -> None:
    """
    Executes the full 6-stage document processing pipeline for a given document.
    Can be called synchronously or via BackgroundTasks.
    """
    async def _run(db: AsyncSession):
        result = await db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            return

        storage_service = get_storage_service()
        try:
            document.processing_status = DocumentStatus.PROCESSING
            await db.flush()

            # Read file from storage
            file_bytes = await storage_service.get(document.storage_path)

            # Reset AI provider singleton so updated settings/.env values are always picked up
            ai_services._default_ai_provider = None

            processor = build_document_processor(storage_service)
            ctx = ProcessingContext(
                user_id=user_id,
                document_id=document_id,
                original_filename=document.original_filename,
                file_data=file_bytes,
                content_type=document.mime_type,
                file_size=document.file_size,
                storage_path=document.storage_path,
                validated_mime_type=document.mime_type,
            )

            # Run full 6-stage pipeline
            ctx = await processor.process(ctx)

            # Update document record
            document.document_type = ctx.document_type
            document.processing_status = ctx.processing_status
            document.extraction_confidence = ctx.confidence_score
            document.processed_at = datetime.now(timezone.utc)
            await db.flush()

            # Save extraction result with provenance and metadata
            extraction_service = ExtractionService(db)
            val_status = (
                ValidationStatus.VALID
                if (ctx.confidence_score or 0) >= settings.EXTRACTION_CONFIDENCE_THRESHOLD
                else ValidationStatus.PENDING
            )

            await extraction_service.save_extraction_result(
                document_id=document.id,
                extracted_json=ctx.extraction_result,
                confidence_score=ctx.confidence_score,
                validation_status=val_status,
                field_evidence=ctx.field_evidence,
                processing_metadata={
                    "ocr_used": ctx.ocr_used,
                    "pages_processed": ctx.page_count,
                    "processing_duration": ctx.duration_seconds,
                    "model_name": settings.AI_MODEL,
                    "extraction_version": "2.0",
                    "pages": ctx.pages,
                    "full_text": ctx.extracted_text,
                },
                schema_version="2.0",
            )

            # Create notification
            notification_service = NotificationService(db)
            if ctx.processing_status == DocumentStatus.COMPLETED:
                await notification_service.create_processing_complete_notification(
                    user_id=user_id,
                    document=document,
                    confidence=ctx.confidence_score,
                )
            elif ctx.processing_status == DocumentStatus.NEEDS_REVIEW:
                await notification_service.create_needs_review_notification(
                    user_id=user_id,
                    document=document,
                )
            elif ctx.processing_status == DocumentStatus.FAILED:
                await notification_service.create_failed_notification(
                    user_id=user_id,
                    document=document,
                )

            await db.commit()
            ProcessingTracker.mark_complete(document_id, ctx.processing_status.value)
            logger.info("Pipeline completed successfully", document_id=str(document_id), status=ctx.processing_status.value)

        except Exception as e:
            logger.error("Pipeline execution failed", document_id=str(document_id), error=str(e))
            try:
                document.processing_status = DocumentStatus.FAILED
                notif = NotificationService(db)
                await notif.create_failed_notification(user_id=user_id, document=document, reason=str(e))
                await db.commit()
            except Exception:
                pass
            ProcessingTracker.mark_failed(document_id, str(e))

    if session:
        await _run(session)
    else:
        async with AsyncSessionLocal() as new_session:
            await _run(new_session)


@router.post(
    "/upload",
    response_model=APIResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload one or more documents",
)
async def upload_documents(
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="One or more files to upload"),
    sync: bool = Query(False, description="Run processing synchronously before returning"),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentUploadResponse]:
    """
    Upload document(s). Validates, persists to storage, creates queued record,
    and runs the AI extraction pipeline asynchronously.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided.",
        )

    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files per upload request.",
        )

    storage_service = get_storage_service()
    notification_service = NotificationService(db)
    uploaded_documents: List[Document] = []

    for file in files:
        file_data = await file.read()
        filename = file.filename or "unnamed"
        content_type = file.content_type or "application/octet-stream"

        try:
            # 1. File Validation
            validated_mime = validate_file(
                filename=filename,
                content_type=content_type,
                file_size=len(file_data),
            )

            # 2. File Storage
            storage_path = await storage_service.save(
                file_data=file_data,
                filename=filename,
                user_id=current_user.id,
                content_type=validated_mime,
            )

            # 3. Create Document Record with QUEUED status
            file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
            document = Document(
                user_id=current_user.id,
                original_filename=filename,
                file_type=file_ext,
                mime_type=validated_mime,
                file_size=len(file_data),
                storage_path=storage_path,
                document_type=DocumentType.UNKNOWN,
                processing_status=DocumentStatus.QUEUED,
                extraction_confidence=None,
            )
            db.add(document)
            await db.flush()
            await db.refresh(document)

            # 4. Create initial upload notification
            await notification_service.create_upload_notification(
                user_id=current_user.id,
                document=document,
            )

            # 5. Initialize live processing tracker
            ProcessingTracker.init_document(document.id, "queued")

            uploaded_documents.append(document)

        except FileValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": e.code, "message": str(e)},
            )

    await db.commit()

    # Trigger processing pipeline for uploaded documents
    for doc in uploaded_documents:
        if sync:
            await execute_pipeline_for_document(doc.id, current_user.id, session=db)
            await db.refresh(doc)
        else:
            background_tasks.add_task(execute_pipeline_for_document, doc.id, current_user.id)

    primary_doc = uploaded_documents[0]
    return APIResponse.ok(
        DocumentUploadResponse(
            document=DocumentResponse.model_validate(primary_doc),
            message=f"{len(uploaded_documents)} document(s) uploaded and queued for processing.",
        )
    )


@router.get(
    "",
    response_model=APIResponse[DocumentListResponse],
    summary="List documents with filtering and pagination",
)
async def list_documents(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[DocumentStatus] = Query(None, alias="status", description="Filter by status"),
    doc_type: Optional[DocumentType] = Query(None, alias="document_type", description="Filter by type"),
    search: Optional[str] = Query(None, description="Search in filename"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort direction (asc/desc)"),
) -> APIResponse[DocumentListResponse]:
    """List documents belonging to the authenticated user."""
    conditions = [Document.user_id == current_user.id]

    if status_filter:
        conditions.append(Document.processing_status == status_filter)
    if doc_type:
        conditions.append(Document.document_type == doc_type)
    if search:
        search_escaped = search.replace("%", r"\%").replace("_", r"\_")
        conditions.append(Document.original_filename.ilike(f"%{search_escaped}%"))

    # Count total
    count_query = select(func.count(Document.id)).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Fetch page
    sort_column = getattr(Document, sort_by, Document.created_at)
    order_clause = sort_column.asc() if sort_order.lower() == "asc" else sort_column.desc()

    offset = (page - 1) * size
    query = (
        select(Document)
        .where(and_(*conditions))
        .order_by(order_clause)
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(query)
    documents = result.scalars().all()

    pages = max(1, (total + size - 1) // size)
    return APIResponse.ok(
        DocumentListResponse(
            items=[DocumentResponse.model_validate(d) for d in documents],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    )


@router.get(
    "/{document_id}",
    response_model=APIResponse[DocumentResponse],
    summary="Get document details",
)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentResponse]:
    """Get a single document by ID."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return APIResponse.ok(DocumentResponse.model_validate(document))


@router.delete(
    "/{document_id}",
    response_model=APIResponse[DocumentDeleteResponse],
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentDeleteResponse]:
    """Delete a document, its stored file, and its extraction results."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if document.storage_path:
        try:
            storage_service = get_storage_service()
            await storage_service.delete(document.storage_path)
        except Exception as e:
            logger.warning("Failed to delete file from storage", storage_path=document.storage_path, error=str(e))

    await db.delete(document)
    return APIResponse.ok(DocumentDeleteResponse())


@router.get(
    "/{document_id}/extraction",
    response_model=APIResponse[ExtractionResultDetail],
    summary="Get extraction results for a document",
)
async def get_extraction(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ExtractionResultDetail]:
    """Get extraction results, field provenance evidence, and audit history."""
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    extraction_service = ExtractionService(db)
    result = await extraction_service.get_by_document_id(document_id)
    detail = extraction_service.format_detail(result)
    return APIResponse.ok(detail)


@router.put(
    "/{document_id}/extraction",
    response_model=APIResponse[ExtractionResultDetail],
    summary="Update or manually validate extraction results",
)
async def update_extraction(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    updated_data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ExtractionResultDetail]:
    """Update extraction fields with user corrections while preserving audit trail."""
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    extraction_service = ExtractionService(db)
    result = await extraction_service.update_extracted_json(
        document_id=document_id,
        updated_data=updated_data,
        user_identifier=current_user.email,
        validation_status=ValidationStatus.VALID,
    )
    detail = extraction_service.format_detail(result)
    return APIResponse.ok(detail)


@router.post(
    "/{document_id}/process",
    response_model=APIResponse[ProcessingStatusResponse],
    summary="Start processing a document",
)
async def process_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    sync: bool = Query(False, description="Run synchronously"),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ProcessingStatusResponse]:
    """Trigger or start processing for a document."""
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    ProcessingTracker.init_document(document_id, "processing")
    if sync:
        await execute_pipeline_for_document(document_id, current_user.id, db)
        await db.refresh(document)
    else:
        background_tasks.add_task(execute_pipeline_for_document, document_id, current_user.id)

    status_resp = ProcessingTracker.get_status(document_id, document)
    return APIResponse.ok(status_resp)


@router.post(
    "/{document_id}/reprocess",
    summary="Reprocess an existing document through OCR and AI extraction",
)
async def reprocess_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    sync: bool = Query(True, description="Run synchronously and return updated extraction result"),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[Any]:
    """Trigger reprocessing of a document. Runs pipeline and returns extraction result."""
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # Mark as processing and init tracker
    document.processing_status = DocumentStatus.PROCESSING
    await db.commit()
    ProcessingTracker.init_document(document_id, "processing")

    if sync:
        await execute_pipeline_for_document(document_id, current_user.id, db)
        extraction_service = ExtractionService(db)
        result = await extraction_service.get_by_document_id(document_id)
        if result:
            detail = extraction_service.format_detail(result)
            return APIResponse.ok(detail)
        status_resp = ProcessingTracker.get_status(document_id, document)
        return APIResponse.ok(status_resp)
    else:
        background_tasks.add_task(execute_pipeline_for_document, document_id, current_user.id)
        status_resp = ProcessingTracker.get_status(document_id, document)
        return APIResponse.ok(status_resp)


@router.get(
    "/{document_id}/text",
    response_model=APIResponse[DocumentTextResponse],
    summary="Get extracted text and page breakdown",
)
async def get_document_text(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentTextResponse]:
    """Return raw extracted text and page-by-page breakdown with OCR usage indicator."""
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    extraction_service = ExtractionService(db)
    ext_result = await extraction_service.get_by_document_id(document_id)

    data = ext_result.extracted_json if ext_result else {}
    proc_meta = data.get("processing_metadata", {}) if data else {}

    pages = proc_meta.get("pages", [])
    full_text = proc_meta.get("full_text", "")
    ocr_used = bool(proc_meta.get("ocr_used", False))

    # If not saved in metadata, re-extract pages dynamically
    if not pages:
        storage_service = get_storage_service()
        file_bytes = await storage_service.get(document.storage_path)
        from app.services.text_extraction_service import DocumentTextExtractor
        extractor = DocumentTextExtractor()
        pages_res = extractor.extract_pages(file_bytes, document.original_filename, document.mime_type)
        pages = [p.to_dict() for p in pages_res.pages]
        full_text = pages_res.full_text
        ocr_used = pages_res.ocr_used

    total_chars = sum(len(p.get("text", "")) for p in pages)
    return APIResponse.ok(
        DocumentTextResponse(
            document_id=document_id,
            total_pages=len(pages),
            total_characters=total_chars,
            is_scanned=ocr_used,
            ocr_used=ocr_used,
            pages=pages,
            full_text=full_text,
        )
    )


@router.get(
    "/{document_id}/processing-status",
    response_model=APIResponse[ProcessingStatusResponse],
    summary="Get real-time document processing stage status",
)
async def get_processing_status(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ProcessingStatusResponse]:
    """Return stage-by-stage status of document processing."""
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    status_resp = ProcessingTracker.get_status(document_id, document)
    return APIResponse.ok(status_resp)


@router.get(
    "/{document_id}/file",
    summary="Download or stream the original document file",
)
async def get_document_file(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Streams the stored document file for in-browser preview or download."""
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    storage_service = get_storage_service()
    try:
        file_bytes = await storage_service.get(document.storage_path)
        return Response(
            content=file_bytes,
            media_type=document.mime_type,
            headers={
                "Content-Disposition": f'inline; filename="{document.original_filename}"'
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found on storage: {str(e)}",
        )


@router.get(
    "/{document_id}/debug-annotation",
    summary="Get internal developer debug annotated image with bounding boxes and label->value mappings",
)
async def get_debug_annotation(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number to annotate"),
    db: AsyncSession = Depends(get_db),
):
    """
    Developer / debug mode visual diagnostic endpoint (Section 18).
    Renders an annotated page showing:
    - Detected text bounding boxes
    - OCR text and confidence badges
    - Layout regions
    - Table regions
    - Field labels (Amber)
    - Selected field values (Bright Green)
    - Directed arrows from [Label] -> [Value]
    - Source bounding boxes
    """
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # 1. Check if cached debug annotation exists on disk
    cfg = get_settings()
    debug_file = cfg.storage_path_resolved / "debug" / f"{document_id}_p{page}.jpg"
    if debug_file.exists():
        try:
            return Response(content=debug_file.read_bytes(), media_type="image/jpeg")
        except Exception:
            pass

    # 2. Dynamic generation if not pre-cached
    storage_service = get_storage_service()
    try:
        file_bytes = await storage_service.get(document.storage_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source document file not found: {str(e)}",
        )

    try:
        from app.services.vision.page_renderer import PageRenderer
        from app.services.vision.image_preprocessor import ImagePreprocessor
        from app.services.vision.paddle_vision_service import PaddleVisionService
        from app.services.vision.spatial_associator import SpatialAssociator
        from app.services.vision.annotation_service import AnnotationService

        rendered_pages = PageRenderer.render_document(
            file_bytes=file_bytes,
            mime_type=document.mime_type,
            filename=document.original_filename,
            dpi=300,
        )
        target_page = next((p for p in rendered_pages if p.page_number == page), rendered_pages[0] if rendered_pages else None)
        if not target_page:
            raise HTTPException(status_code=404, detail="Page not found")

        img_deskewed, _ = ImagePreprocessor.detect_and_deskew(target_page.numpy_image)
        img_enhanced = ImagePreprocessor.enhance_for_ocr(img_deskewed, apply_clahe=True, apply_sharpen=True)
        page_res = PaddleVisionService.process_page(
            image_rgb=img_enhanced,
            page_number=target_page.page_number,
            enable_tiling=True,
            enable_layout=True,
        )
        page_cands = SpatialAssociator.associate_fields_for_page(page_res)
        jpeg_bytes = AnnotationService.get_annotated_jpeg_bytes(
            base_image_rgb=img_deskewed,
            vision_result=page_res,
            field_candidates=page_cands,
        )
        return Response(content=jpeg_bytes, media_type="image/jpeg")
    except Exception as e:
        logger.error("Failed to generate debug annotation", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating debug annotation: {str(e)}",
        )
