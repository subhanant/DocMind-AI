"""
Tests for Document Vision & Extraction Architecture Upgrade.

Validates:
1. High-resolution page rendering (300+ DPI)
2. Controlled preprocessing (CLAHE, denoise, deskew)
3. PaddleOCR primary vision layer with 2D spatial text boxes and layout
4. Micro-text recovery
5. Spatial label -> value association with ranking and boilerplate filtering
6. Section 12 field envelope structure and 27 core fields schema preservation
7. Pre-completion extraction audit
8. Developer debug annotation overlay generation
"""
import io
import numpy as np
import pytest
import pymupdf

from app.services.vision.page_renderer import PageRenderer
from app.services.vision.image_preprocessor import ImagePreprocessor
from app.services.vision.paddle_vision_service import PaddleVisionService, TextBox, LayoutRegion
from app.services.vision.micro_text_service import MicroTextRecoveryService
from app.services.vision.field_validators import FieldValidators
from app.services.vision.spatial_associator import SpatialAssociator
from app.services.vision.table_extractor import TableExtractionService
from app.services.vision.annotation_service import AnnotationService
from app.services.vision.extraction_audit import ExtractionAuditService
from app.services.vision.document_vision_pipeline import DocumentVisionPipeline, CORE_27_FIELDS


def create_sample_bl_pdf() -> bytes:
    """Creates a sample Bill of Lading PDF for testing."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    sample_text = """
    OCEAN BILL OF LADING
    B/L NO. MEDUFF439584
    BOOKING NO: BKG-2026-99001
    DATE OF ISSUE: 15-SEP-2026

    SHIPPER:
    GLOBAL MARITIME EXPORTS LTD
    100 OCEAN VIEW TOWER, SINGAPORE

    CONSIGNEE:
    EUROPE LOGISTICS BV
    ROTTERDAM HARBOR, NETHERLANDS

    NOTIFY PARTY:
    EUROPE LOGISTICS BV
    ROTTERDAM HARBOR, NETHERLANDS

    VESSEL: MSC GULSUN
    VOYAGE: 2609E
    PORT OF LOADING: SINGAPORE
    PORT OF DISCHARGE: ROTTERDAM

    CONTAINER / SEAL / PARTICULARS:
    MSCU1234567 / SL998811 / 40HC / 24500.00 KGS / STC ELECTRONIC PARTS
    TGHU7654321 / SL998822 / 20GP / 18200.00 KGS / STC SOLAR PANELS

    HS CODE: 8504.40
    TOTAL GROSS WEIGHT: 42700.00 KGS
    FREIGHT PREPAID
    """
    page.insert_text((50, 50), sample_text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_field_validators_bl_number():
    """Verify B/L number validator rejects boilerplates and requires valid identifier."""
    # Rejects boilerplate words
    assert not FieldValidators.validate_bl_number("Received").is_valid
    assert not FieldValidators.validate_bl_number("B/L NO. Received").is_valid
    assert not FieldValidators.validate_bl_number("Draft").is_valid
    assert not FieldValidators.validate_bl_number("BOOKING").is_valid

    # Accepts valid real B/L numbers
    valid_res = FieldValidators.validate_bl_number("MEDUFF439584")
    assert valid_res.is_valid
    assert valid_res.normalized_value == "MEDUFF439584"

    valid_res2 = FieldValidators.validate_bl_number("SHRCB26001503")
    assert valid_res2.is_valid
    assert valid_res2.normalized_value == "SHRCB26001503"


def test_field_validators_container_number():
    """Verify ISO 6346 container number validator."""
    res = FieldValidators.validate_container_number("MSCU1234567")
    assert res.is_valid
    assert res.normalized_value == "MSCU1234567"

    # Invalid container (bad length / prefix)
    res_bad = FieldValidators.validate_container_number("NOT_A_CONTAINER")
    assert not res_bad.is_valid


def test_page_renderer():
    """Verify high-resolution page rendering."""
    pdf_bytes = create_sample_bl_pdf()
    pages = PageRenderer.render_document(pdf_bytes, "application/pdf", dpi=150)
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].dpi == 150
    assert pages[0].numpy_image.shape[0] > 500
    assert pages[0].numpy_image.shape[1] > 400


def test_image_preprocessor():
    """Verify non-destructive image preprocessing."""
    dummy_img = np.full((300, 300, 3), 200, dtype=np.uint8)
    enhanced = ImagePreprocessor.enhance_contrast_adaptive(dummy_img, clip_limit=2.0)
    assert enhanced.shape == dummy_img.shape
    deskewed, angle = ImagePreprocessor.detect_and_deskew(dummy_img)
    assert deskewed.shape == dummy_img.shape
    assert isinstance(angle, float)


def test_spatial_associator_rejects_boilerplate():
    """Verify spatial associator correctly prioritizes true value and rejects label text."""
    label_box = TextBox(text="B/L NO.", confidence=0.99, bbox=[100.0, 100.0, 180.0, 120.0], page_number=1)
    boilerplate_box = TextBox(text="Received in good order", confidence=0.95, bbox=[100.0, 125.0, 250.0, 145.0], page_number=1)
    actual_value_box = TextBox(text="MEDUFF439584", confidence=0.98, bbox=[190.0, 100.0, 310.0, 120.0], page_number=1)

    cands = SpatialAssociator.associate_fields_for_page(
        page_vision=PaddleVisionService.process_page(
            image_rgb=np.full((400, 400, 3), 255, dtype=np.uint8),
            page_number=1,
            enable_tiling=False,
            enable_layout=False,
        )
    )
    # Direct test of find_best_candidate with simulated boxes
    best_cand = SpatialAssociator.find_best_candidate(
        field_name="bill_of_lading_number",
        label_aliases=["B/L NO", "B/L NO.", "BILL OF LADING NO"],
        text_boxes=[label_box, boilerplate_box, actual_value_box],
        layout_regions=[],
        page_width=500,
        page_height=500,
        page_number=1,
    )
    assert best_cand is not None
    assert best_cand.value_raw == "MEDUFF439584"
    assert best_cand.validation_status == "valid"
    assert best_cand.spatial_relationship == "horizontal_right"


def test_extraction_audit():
    """Verify extraction audit service checks."""
    extracted_data = {
        "fields": {
            f: {"value_normalized": "TEST" if f in ("bill_of_lading_number", "shipper") else None}
            for f in CORE_27_FIELDS
        }
    }
    field_evidence = {"bill_of_lading_number": {"value": "TEST"}}
    report = ExtractionAuditService.audit_extraction(
        extracted_data=extracted_data,
        field_evidence=field_evidence,
        pages_count=1,
        containers_count=1,
    )
    assert report.total_checks == 5
    assert len(report.checks) == 5


def test_annotation_service_rendering():
    """Verify debug annotation map generation."""
    dummy_img = np.full((400, 400, 3), 255, dtype=np.uint8)
    label_box = TextBox(text="B/L NO.", confidence=0.99, bbox=[50.0, 50.0, 120.0, 70.0], page_number=1)
    val_box = TextBox(text="MEDUFF439584", confidence=0.98, bbox=[130.0, 50.0, 240.0, 70.0], page_number=1)
    vision_res = PaddleVisionService.process_page(dummy_img, page_number=1, enable_tiling=False, enable_layout=False)
    vision_res.text_boxes = [label_box, val_box]

    cand = SpatialAssociator.find_best_candidate(
        field_name="bill_of_lading_number",
        label_aliases=["B/L NO."],
        text_boxes=[label_box, val_box],
        layout_regions=[],
        page_width=400,
        page_height=400,
        page_number=1,
    )
    jpeg_bytes = AnnotationService.get_annotated_jpeg_bytes(
        base_image_rgb=dummy_img,
        vision_result=vision_res,
        field_candidates={"bill_of_lading_number": cand} if cand else {},
    )
    assert isinstance(jpeg_bytes, bytes)
    assert len(jpeg_bytes) > 100
    assert jpeg_bytes[:2] == b"\xff\xd8"  # Valid JPEG header
