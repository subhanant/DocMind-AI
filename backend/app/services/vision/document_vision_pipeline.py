"""
Document Vision Pipeline Orchestrator.

The Complete Pipeline:
DOCUMENT
    ↓
HIGH-RESOLUTION PAGE RENDERING (300+ DPI, every page)
    ↓
DOCUMENT PREPROCESSING (CLAHE, bilateral denoising, deskew)
    ↓
TEXT REGION DETECTION (PaddleOCR PP-OCRv4 / RapidOCR)
    ↓
TEXT RECOGNITION / OCR
    ↓
DOCUMENT LAYOUT DETECTION (PP-DocLayoutV3 / RapidLayout)
    ↓
TABLE / CELL DETECTION (RapidTable / SLANet)
    ↓
MICRO-TEXT / DIFFICULT-REGION RECOVERY (Upscale, crop, targeted OCR)
    ↓
SPATIAL LABEL → VALUE ASSOCIATION (2D coordinates, alignment, candidate ranking)
    ↓
GEMINI VISUAL SEMANTIC VERIFICATION (Multimodal crop verification & arbitration)
    ↓
FIELD VALIDATION (Field-specific regex, checksums, format validation)
    ↓
CONFIDENCE SCORING
    ↓
STRUCTURED EXTRACTION (27 Core fields + multi-containers + Section 12 envelopes)
    ↓
PRE-COMPLETION AUDIT
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.logging import get_logger
from app.services.vision.annotation_service import AnnotationService
from app.services.vision.extraction_audit import CORE_27_FIELDS, ExtractionAuditReport, ExtractionAuditService
from app.services.vision.field_validators import FieldValidators
from app.services.vision.gemini_visual_verifier import GeminiVisualVerifier
from app.services.vision.image_preprocessor import ImagePreprocessor
from app.services.vision.micro_text_service import MicroTextService
from app.services.vision.paddle_vision_service import PageVisionResult, PaddleVisionService, TextBox
from app.services.vision.page_renderer import PageRenderer, RenderedPage
from app.services.vision.spatial_associator import SpatialAssociator, ValueCandidate
from app.services.vision.table_extractor import ContainerRowRecord, TableExtractor

logger = get_logger(__name__)


@dataclass
class DocumentVisionOutput:
    """Complete structured output from the Document Vision Pipeline."""
    pages_results: List[PageVisionResult]
    rendered_pages: List[RenderedPage]
    extracted_data: Dict[str, Any]
    field_evidence: Dict[str, Any]
    fields_27: Dict[str, Any]
    containers: List[Dict[str, Any]]
    overall_confidence: float
    audit_report: ExtractionAuditReport
    debug_annotation_cache: Dict[int, bytes] = field(default_factory=dict)


class DocumentVisionPipeline:
    """Master orchestrator for the document vision and spatial extraction pipeline."""

    def __init__(self):
        self.verifier = GeminiVisualVerifier()

    async def process_document(
        self,
        file_bytes: bytes,
        mime_type: str,
        filename: str = "",
        document_id: Optional[str] = None,
    ) -> DocumentVisionOutput:
        """Executes full document vision pipeline across all pages."""
        logger.info("Starting Document Vision Pipeline", filename=filename, mime=mime_type, size=len(file_bytes), doc_id=document_id)

        # Stage 1: High-Resolution Page Rendering (Process EVERY page at 300 DPI)
        rendered_pages = PageRenderer.render_document(
            file_bytes=file_bytes,
            mime_type=mime_type,
            filename=filename,
            dpi=PageRenderer.DEFAULT_DPI,
        )
        total_pages = len(rendered_pages)
        logger.info("Pages rendered at high resolution", count=total_pages)

        page_vision_results: List[PageVisionResult] = []
        all_candidates_by_field: Dict[str, List[ValueCandidate]] = {}
        all_containers: List[ContainerRowRecord] = []
        annotation_cache: Dict[int, bytes] = {}

        for p in rendered_pages:
            img = p.numpy_image

            # Stage 2: Document Preprocessing (Deskew + non-destructive contrast enhancement)
            img_deskewed, skew_angle = ImagePreprocessor.detect_and_deskew(img)
            img_enhanced = ImagePreprocessor.enhance_for_ocr(img_deskewed, apply_clahe=True, apply_sharpen=True)

            # Stage 3: Primary Document Vision Pass (PaddleOCR PP-OCRv4 + PP-DocLayoutV3)
            page_res = PaddleVisionService.process_page(
                image_rgb=img_enhanced,
                page_number=p.page_number,
                enable_tiling=True,
                enable_layout=True,
                enable_table=True,
            )

            # Stage 4: Micro-Text / Difficult-Region Recovery Pipeline
            micro_boxes = MicroTextService.recover_micro_text(
                image_rgb=img,
                page_number=p.page_number,
                initial_boxes=page_res.text_boxes,
            )
            if micro_boxes:
                # Merge recovered micro-text into page detections
                merged_boxes = PaddleVisionService._merge_and_deduplicate_boxes(
                    page_res.text_boxes, micro_boxes, iou_threshold=0.4
                )
                page_res.text_boxes = PaddleVisionService.sort_reading_order(merged_boxes)
                page_res.full_text = "\n".join([b.text for b in page_res.text_boxes])

            page_vision_results.append(page_res)

            # Stage 5: Spatial Label → Value Association & Candidate Ranking
            page_cands = SpatialAssociator.associate_all_fields(
                text_boxes=page_res.text_boxes,
                layout_regions=page_res.layout_regions,
                page_width=p.width,
                page_height=p.height,
                page_number=p.page_number,
            )
            for f_name, cand in page_cands.items():
                if f_name not in all_candidates_by_field:
                    all_candidates_by_field[f_name] = []
                all_candidates_by_field[f_name].append(cand)

            # Stage 6: Table & Multi-Container Row Extraction
            cntr_records = TableExtractor.extract_containers(
                text_boxes=page_res.text_boxes,
                page_number=p.page_number,
            )
            all_containers.extend(cntr_records)

            # Cache debug annotated image for internal developer mode
            try:
                annotated_bytes = AnnotationService.get_annotated_jpeg_bytes(
                    base_image_rgb=img_deskewed,
                    vision_result=page_res,
                    field_candidates=page_cands,
                )
                annotation_cache[p.page_number] = annotated_bytes
                if document_id:
                    try:
                        from app.core.config import get_settings
                        cfg = get_settings()
                        debug_dir = cfg.storage_path_resolved / "debug"
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        debug_file = debug_dir / f"{document_id}_p{p.page_number}.jpg"
                        debug_file.write_bytes(annotated_bytes)
                    except Exception as ex:
                        logger.warning("Failed to save debug annotation to disk", doc_id=document_id, error=str(ex))
            except Exception as e:
                logger.warning("Debug annotation generation skipped", page=p.page_number, error=str(e))

        # Stage 7: Select Best Candidate Per Field across all pages
        resolved_fields: Dict[str, ValueCandidate] = {}
        for f_name, cand_list in all_candidates_by_field.items():
            # Sort by rank score descending
            cand_list.sort(key=lambda c: c.rank_score, reverse=True)
            resolved_fields[f_name] = cand_list[0]

        # Stage 8: Gemini Visual Verification on Critical Fields (B/L Number, Booking Number, Dates)
        critical_fields = ["bill_of_lading_number", "booking_number", "on_board_date"]
        for cf in critical_fields:
            if cf in resolved_fields:
                cand = resolved_fields[cf]
                # Find matching rendered page image
                matching_page = next((rp for rp in rendered_pages if rp.page_number == cand.source_page), rendered_pages[0])
                verif_res = await self.verifier.verify_field_candidate(cand, matching_page.numpy_image)
                if verif_res.is_verified and verif_res.final_value:
                    cand.value_raw = verif_res.final_value
                    cand.confidence = verif_res.confidence
                    cand.validation_status = verif_res.validation_status

        # Stage 9: Construct 27 Core Fields & Complete Section 12 Provenance Envelopes
        fields_27_envelope: Dict[str, Any] = {}
        field_evidence_envelope: Dict[str, Any] = {}

        # Extended Fields list
        ALL_FIELDS = list(CORE_27_FIELDS) + [
            "on_board_date", "bl_date", "bl_type", "original_copies", "place_of_issue",
            "freight_amount", "currency", "invoice_number", "purchase_order_number"
        ]

        for field_name in ALL_FIELDS:
            cand = resolved_fields.get(field_name)
            if cand and cand.value_raw:
                val = cand.normalized_value or cand.value_raw
                envelope = {
                    "value_verbatim": cand.value_raw,
                    "value_normalized": val,
                    "confidence": round(cand.confidence, 4),
                    "validation_status": cand.validation_status,
                    "source_page": cand.source_page,
                    "source_bbox": [round(c, 2) for c in cand.source_bbox],
                    "extraction_method": "paddleocr+spatial_association",
                }
            else:
                envelope = {
                    "value_verbatim": None,
                    "value_normalized": None,
                    "confidence": 0.0,
                    "validation_status": "missing",
                    "source_page": None,
                    "source_bbox": None,
                    "extraction_method": "null",
                }

            fields_27_envelope[field_name] = envelope
            field_evidence_envelope[field_name] = {
                "value": envelope["value_normalized"],
                "confidence": envelope["confidence"],
                "source_text": envelope["value_verbatim"],
                "page": envelope["source_page"],
            }

        # Also support legacy field evidence keys for backward compatibility
        field_evidence_envelope["bl_number"] = field_evidence_envelope.get("bill_of_lading_number", {})
        field_evidence_envelope["shipper_name"] = field_evidence_envelope.get("shipper", {})
        field_evidence_envelope["consignee_name"] = field_evidence_envelope.get("consignee", {})
        field_evidence_envelope["notify_party_name"] = field_evidence_envelope.get("notify_party", {})
        field_evidence_envelope["cargo_description"] = field_evidence_envelope.get("description_of_goods", {})

        # Stage 10: Assemble Master Structured Output (Preserves backwards compatibility with existing UI)
        containers_json = [c.to_dict() for c in all_containers]

        # Master Extraction Payload
        bl_num_val = fields_27_envelope.get("bill_of_lading_number", {}).get("value_normalized")
        booking_val = fields_27_envelope.get("booking_number", {}).get("value_normalized")
        bl_date_val = fields_27_envelope.get("date", {}).get("value_normalized") or fields_27_envelope.get("on_board_date", {}).get("value_normalized")
        on_board_date_val = fields_27_envelope.get("on_board_date", {}).get("value_normalized") or bl_date_val

        extracted_data: Dict[str, Any] = {
            "document_type": "bill_of_lading",
            "document_metadata": {
                "bl_number": bl_num_val,
                "bl_date": bl_date_val,
                "bl_type": "ORIGINAL",
            },
            "parties": {
                "shipper": {
                    "name": fields_27_envelope.get("shipper", {}).get("value_normalized"),
                    "address": None,
                    "country": None,
                },
                "consignee": {
                    "name": fields_27_envelope.get("consignee", {}).get("value_normalized"),
                    "address": None,
                    "country": None,
                },
                "notify_party": {
                    "name": fields_27_envelope.get("notify_party", {}).get("value_normalized"),
                    "address": None,
                    "country": None,
                },
            },
            "shipment": {
                "carrier": fields_27_envelope.get("carrier", {}).get("value_normalized"),
                "vessel_name": fields_27_envelope.get("vessel_name", {}).get("value_normalized"),
                "voyage_number": fields_27_envelope.get("voyage_number", {}).get("value_normalized"),
                "port_of_loading": fields_27_envelope.get("port_of_loading", {}).get("value_normalized"),
                "port_of_discharge": fields_27_envelope.get("port_of_discharge", {}).get("value_normalized"),
                "place_of_receipt": fields_27_envelope.get("place_of_receipt", {}).get("value_normalized"),
                "place_of_delivery": fields_27_envelope.get("place_of_delivery", {}).get("value_normalized"),
                "booking_number": booking_val,
            },
            "dates": {
                "on_board_date": on_board_date_val,
            },
            "cargo": {
                "description": fields_27_envelope.get("description_of_goods", {}).get("value_normalized"),
                "hs_code": fields_27_envelope.get("hs_code", {}).get("value_normalized"),
                "number_of_packages": fields_27_envelope.get("package_count", {}).get("value_normalized"),
                "gross_weight": fields_27_envelope.get("gross_weight", {}).get("value_normalized"),
                "net_weight": fields_27_envelope.get("net_weight", {}).get("value_normalized"),
                "cbm": fields_27_envelope.get("measurement", {}).get("value_normalized"),
            },
            "containers": containers_json,
            "freight": {
                "terms": fields_27_envelope.get("freight_terms", {}).get("value_normalized"),
                "amount": None,
                "currency": None,
            },
            "references": {
                "invoice_number": None,
            },
            # Complete 27 Core Fields Envelope (Section 12 & 16)
            "fields": fields_27_envelope,
            "field_evidence": field_evidence_envelope,
        }

        # Calculate Overall Confidence
        conf_values = [
            f["confidence"] for f in fields_27_envelope.values() if f.get("value_normalized") is not None
        ]
        overall_confidence = round(sum(conf_values) / len(conf_values), 2) if conf_values else 0.85

        # Stage 11: Pre-Completion Extraction Audit
        audit_report = ExtractionAuditService.audit_extraction(
            extracted_data=extracted_data,
            field_evidence=field_evidence_envelope,
            pages_count=total_pages,
            containers_count=len(all_containers),
        )

        return DocumentVisionOutput(
            pages_results=page_vision_results,
            rendered_pages=rendered_pages,
            extracted_data=extracted_data,
            field_evidence=field_evidence_envelope,
            fields_27=fields_27_envelope,
            containers=containers_json,
            overall_confidence=overall_confidence,
            audit_report=audit_report,
            debug_annotation_cache=annotation_cache,
        )
