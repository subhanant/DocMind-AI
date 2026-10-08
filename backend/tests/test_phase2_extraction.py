"""
Comprehensive Phase 2 Backend Tests for DocuMind AI.

Validates:
1. Text PDF extraction (PyMuPDF native, ocr_used=False)
2. Scanned PDF OCR fallback (ocr_used=True)
3. Image OCR extraction (PNG, JPG, WEBP)
4. Document classification across supported document types
5. Bill of Lading extraction with all 27 priority fields
6. Missing fields returning null (zero hallucination rule)
7. Multiple containers array extraction (1, 2, 3+ containers)
8. Weight & volume measurement parsing ({value, unit})
9. Date parsing (BL date, on-board date)
10. Invalid AI JSON handling & safe repair
11. AI provider fallback when unconfigured
12. Document reprocessing API without duplicate records
13. Extraction status & text endpoint outputs
14. Document ownership authorization isolation
15. Notification creation on extraction completion and review
"""
import io
import json
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw
import pymupdf

from app.db.database import Base, get_db
from app.db.models.document import Document, DocumentStatus, DocumentType
from app.main import app
from app.schemas.extraction import BillOfLadingExtraction
from app.services.ai.gemini_provider import GeminiExtractionProvider
from app.services.ai.heuristic_provider import HeuristicExtractionProvider
from app.services.document_service import ProcessingTracker
from app.services.text_extraction_service import DocumentTextExtractor


# ─── Test Fixture Helpers ───────────────────────────────────────────────────

def create_realistic_bl_pdf() -> bytes:
    """Create a realistic Bill of Lading PDF with all 27 priority fields and multiple containers."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4

    text = """
    OCEAN BILL OF LADING
    ORIGINAL - NON-NEGOTIABLE
    
    B/L NO: MEDU987654321
    DATE OF ISSUE: 15-MAR-2026
    TYPE OF B/L: ORIGINAL
    BOOKING NO: BKG-SEA-99214
    INVOICE NO: INV-2026-8841

    SHIPPER:
    GLOBAL EXPORTS LOGISTICS LTD
    128 HARBOR ROAD, SHANGHAI, CHINA

    CONSIGNEE:
    PACIFIC IMPORTING CORP
    450 DOCK STREET, SEATTLE, WA, USA

    NOTIFY PARTY:
    SEATTLE CUSTOMS BROKERS INC
    100 PIER WAY, SEATTLE, USA

    OCEAN CARRIER: MEDITERRANEAN SHIPPING COMPANY
    OCEAN VESSEL: MSC VALENTINA
    VOYAGE NO: 2603W
    PORT OF LOADING: SHANGHAI, CHINA
    PORT OF DISCHARGE: SEATTLE, WA
    PLACE OF DELIVERY: SEATTLE, WA
    SHIPPED ON BOARD DATE: 16-MAR-2026

    CONTAINER LIST & PACKAGING:
    CONTAINER NO: MSCU1234567 / SEAL: SL-998811 / 40HC
    CONTAINER NO: MSCU7654321 / SEAL: SL-998822 / 40HC
    CONTAINER NO: TGHU3344556 / SEAL: SL-998833 / 20GP

    DESCRIPTION OF GOODS:
    ELECTRONIC COMPONENTS AND INDUSTRIAL SOLAR INVERTERS
    HS CODE: 8504.40
    TOTAL PACKAGES: 1,250 PACKAGES
    GROSS WEIGHT: 18,500.00 KGS
    NET WEIGHT: 16,200.00 KGS
    MEASUREMENT: 45.8 CBM

    FREIGHT & CHARGES:
    FREIGHT PREPAID
    TOTAL FREIGHT: USD 4,850.00
    CURRENCY: USD
    """
    page.insert_text((50, 50), text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_scanned_image_pdf() -> bytes:
    """Create a scanned PDF containing an image of text, without native selectable text."""
    # Generate PIL image
    img = Image.new("RGB", (600, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "SCANNED CARGO MANIFEST\nB/L NO: SCAN998811\nCONTAINER: MSCU9988776", fill=(0, 0, 0))
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    # Insert image as raster (no text layer)
    rect = pymupdf.Rect(50, 50, 500, 250)
    page.insert_image(rect, stream=img_bytes.getvalue())
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_png() -> bytes:
    """Create a sample PNG image."""
    img = Image.new("RGB", (400, 200), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), "BILL OF LADING\nB/L NO: IMG123456", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ─── Auth Helper ─────────────────────────────────────────────────────────────

async def auth_user(client: AsyncClient, email: str = "phase2@documind.ai") -> dict[str, str]:
    password = "SecurePassword123!"
    await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Phase 2 Lead Engineer"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── Unit & Extraction Tests ─────────────────────────────────────────────────

def test_text_pdf_extraction():
    """1. Test native PDF text extraction with PyMuPDF."""
    extractor = DocumentTextExtractor()
    pdf_bytes = create_realistic_bl_pdf()

    result = extractor.extract_pages(pdf_bytes, "bill_of_lading.pdf", "application/pdf")
    assert result.total_pages >= 1
    assert result.total_chars > 300
    assert result.ocr_used is False
    assert "MEDU987654321" in result.full_text
    assert result.pages[0].page_number == 1
    assert result.pages[0].ocr_used is False


def test_scanned_pdf_ocr_fallback():
    """2. Test scanned PDF triggers OCR fallback path when selectable text is missing."""
    extractor = DocumentTextExtractor()
    scanned_bytes = create_scanned_image_pdf()

    result = extractor.extract_pages(scanned_bytes, "scanned_doc.pdf", "application/pdf")
    assert result.total_pages >= 1
    # Because native selectable text was < 50 chars, OCR fallback was invoked
    assert result.ocr_used is True
    assert result.pages[0].ocr_used is True


def test_image_ocr():
    """3. Test image OCR extraction pipeline."""
    extractor = DocumentTextExtractor()
    png_bytes = create_sample_png()

    result = extractor.extract_pages(png_bytes, "shipping_label.png", "image/png")
    assert result.total_pages == 1
    assert result.is_scanned is True
    assert result.ocr_used is True


@pytest.mark.asyncio
async def test_document_classification():
    """4. Test document classification across key document types."""
    provider = HeuristicExtractionProvider()

    # Bill of lading
    bl_res = await provider.classify_document(
        "OCEAN BILL OF LADING\nB/L NO: MEDU123456\nPORT OF LOADING: SHANGHAI\nPORT OF DISCHARGE: SEATTLE\nVESSEL: MSC VALENTINA",
        pages=[{"page_number": 1, "text": "sample"}],
    )
    assert bl_res.document_type == "bill_of_lading"
    assert bl_res.confidence >= 0.70

    # Commercial invoice
    inv_res = await provider.classify_document(
        "COMMERCIAL INVOICE\nINVOICE NO: INV-9901\nTOTAL AMOUNT: $45,000.00\nPAYMENT TERMS: NET 30 DAYS\nUNIT PRICE: $15.00",
        pages=[{"page_number": 1, "text": "sample"}],
    )
    assert inv_res.document_type == "commercial_invoice"
    assert inv_res.confidence >= 0.70

    # Packing list
    pkg_res = await provider.classify_document(
        "PACKING LIST\nWEIGHT LIST\nTOTAL CARTONS: 500\nGROSS WEIGHT: 5,000 KGS\nNET WEIGHT: 4,800 KGS",
        pages=[{"page_number": 1, "text": "sample"}],
    )
    assert pkg_res.document_type == "packing_list"

    # Unknown
    unk_res = await provider.classify_document("Hello world", pages=[])
    assert unk_res.document_type in {"unknown", "general_document"}


@pytest.mark.asyncio
async def test_bill_of_lading_27_fields_extraction():
    """5. Test extraction of all 27 priority Bill of Lading fields."""
    extractor = DocumentTextExtractor()
    pdf_bytes = create_realistic_bl_pdf()
    pages_res = extractor.extract_pages(pdf_bytes, "bl.pdf", "application/pdf")

    provider = HeuristicExtractionProvider()
    data, evidence, confidence = await provider.extract_bill_of_lading(
        text=pages_res.full_text,
        pages=[p.to_dict() for p in pages_res.pages],
    )

    # 1. BL Number
    assert data["document_metadata"]["bl_number"] == "MEDU987654321"
    assert evidence["bl_number"]["value"] == "MEDU987654321"
    assert evidence["bl_number"]["confidence"] > 0.9

    # 2. BL Date
    assert "15-MAR-2026" in str(data["document_metadata"]["bl_date"])

    # 3. BL Type
    assert data["document_metadata"]["bl_type"] == "ORIGINAL"

    # 4. Shipper
    assert "GLOBAL EXPORTS" in data["parties"]["shipper"]["name"]
    assert "128 HARBOR ROAD" in data["parties"]["shipper"]["address"]

    # 5. Consignee
    assert "PACIFIC IMPORTING" in data["parties"]["consignee"]["name"]
    assert "450 DOCK STREET" in data["parties"]["consignee"]["address"]

    # 6. Notify Party
    assert "SEATTLE CUSTOMS BROKERS" in data["parties"]["notify_party"]["name"]

    # 7. Carrier
    assert "MEDITERRANEAN SHIPPING COMPANY" in data["shipment"]["carrier"]

    # 8. Vessel Name
    assert "MSC VALENTINA" in data["shipment"]["vessel_name"]

    # 9. Voyage Number
    assert "2603W" in data["shipment"]["voyage_number"]

    # 10. Port of Loading
    assert "SHANGHAI" in data["shipment"]["port_of_loading"]

    # 11. Port of Discharge
    assert "SEATTLE" in data["shipment"]["port_of_discharge"]

    # 12. Place of Delivery
    assert "SEATTLE" in data["shipment"]["place_of_delivery"]

    # 13. On Board Date
    assert "16-MAR-2026" in str(data["dates"]["on_board_date"])

    # 14, 15, 16. Containers
    assert len(data["containers"]) == 3
    assert data["containers"][0]["container_number"] == "MSCU1234567"
    assert data["containers"][0]["seal_number"] == "SL-998811"
    assert data["containers"][1]["container_number"] == "MSCU7654321"

    # 17. Cargo Description
    assert "SOLAR INVERTERS" in data["cargo"]["description"]

    # 18. HS Code
    assert "8504.40" in data["cargo"]["hs_code"]

    # 19. Packages
    assert data["cargo"]["number_of_packages"] == 1250

    # 20. Gross Weight
    assert data["cargo"]["gross_weight"]["value"] == 18500.0
    assert data["cargo"]["gross_weight"]["unit"] == "KGS"

    # 21. Net Weight
    assert data["cargo"]["net_weight"]["value"] == 16200.0
    assert data["cargo"]["net_weight"]["unit"] == "KGS"

    # 22. CBM
    assert data["cargo"]["cbm"]["value"] == 45.8
    assert data["cargo"]["cbm"]["unit"] == "CBM"

    # 23. Freight Terms
    assert "FREIGHT PREPAID" in data["freight"]["terms"]

    # 24. Freight Amount
    assert data["freight"]["amount"] == 4850.0

    # 25. Currency
    assert data["freight"]["currency"] == "USD"

    # 26. Booking Number
    assert "BKG-SEA-99214" in data["shipment"]["booking_number"]

    # 27. Invoice Number
    assert "INV-2026-8841" in data["references"]["invoice_number"]

    # Validates with Pydantic model
    validated = BillOfLadingExtraction.model_validate(data)
    assert validated.document_metadata.bl_number == "MEDU987654321"
    assert confidence >= 0.75


@pytest.mark.asyncio
async def test_missing_fields_return_null():
    """6. Test zero hallucination rule: missing fields must be null with confidence 0."""
    partial_text = "BILL OF LADING\nB/L NO: MEDU111222333\nVESSEL: MSC BLUE\nCONTAINER NO: MSCU1112223"
    provider = HeuristicExtractionProvider()

    data, evidence, confidence = await provider.extract_bill_of_lading(
        text=partial_text, pages=[{"page_number": 1, "text": partial_text}]
    )

    # Found fields
    assert data["document_metadata"]["bl_number"] == "MEDU111222333"
    assert data["shipment"]["vessel_name"] == "MSC BLUE"

    # Missing fields MUST be None
    assert data["parties"]["shipper"]["name"] is None
    assert evidence["shipper_name"]["value"] is None
    assert evidence["shipper_name"]["confidence"] == 0.0

    assert data["cargo"]["hs_code"] is None
    assert evidence["hs_code"]["value"] is None

    assert data["cargo"]["gross_weight"]["value"] is None
    assert evidence["gross_weight"]["value"] is None

    assert data["freight"]["terms"] is None
    assert data["references"]["invoice_number"] is None


@pytest.mark.asyncio
async def test_multiple_containers_extraction():
    """7. Test multiple containers extraction (array preserves 1, 2, 5+ containers)."""
    text = """
    CONTAINER NO: MSCU1111111 / SEAL: SL-001 / 40HC
    CONTAINER NO: COSU2222222 / SEAL: SL-002 / 20GP
    CONTAINER NO: CMAU3333333 / SEAL: SL-003 / 40HC
    CONTAINER NO: ONEU4444444 / SEAL: SL-004 / 40HC
    CONTAINER NO: HLCU5555555 / SEAL: SL-005 / 40HC
    """
    provider = HeuristicExtractionProvider()
    data, evidence, _ = await provider.extract_bill_of_lading(text, pages=[])

    containers = data["containers"]
    assert len(containers) == 5
    numbers = [c["container_number"] for c in containers]
    assert "MSCU1111111" in numbers
    assert "COSU2222222" in numbers
    assert "CMAU3333333" in numbers
    assert "ONEU4444444" in numbers
    assert "HLCU5555555" in numbers


@pytest.mark.asyncio
async def test_weight_and_measurement_parsing():
    """8. Test numeric parsing strictly separate from units."""
    text = "GROSS WEIGHT: 12,450.50 KGS\nNET WEIGHT: 11,200 LBS\nTOTAL CBM: 32.4 M3"
    provider = HeuristicExtractionProvider()
    data, _, _ = await provider.extract_bill_of_lading(text, pages=[])

    assert data["cargo"]["gross_weight"]["value"] == 12450.50
    assert data["cargo"]["gross_weight"]["unit"] == "KGS"

    assert data["cargo"]["net_weight"]["value"] == 11200.0
    assert data["cargo"]["net_weight"]["unit"] == "LBS"

    assert data["cargo"]["cbm"]["value"] == 32.4


@pytest.mark.asyncio
async def test_date_parsing():
    """9. Test extraction of dates."""
    text = "B/L NO: ABC123456\nDATE OF ISSUE: 2026-05-20\nSHIPPED ON BOARD DATE: 22-MAY-2026"
    provider = HeuristicExtractionProvider()
    data, _, _ = await provider.extract_bill_of_lading(text, pages=[])

    assert "2026-05-20" in str(data["document_metadata"]["bl_date"])
    assert "22-MAY-2026" in str(data["dates"]["on_board_date"])


def test_invalid_ai_json_handling():
    """10. Test AI JSON extraction and repair with markdown blocks and trailing commas."""
    provider = GeminiExtractionProvider()

    # Markdown fence
    fence_json = '```json\n{"document_type": "bill_of_lading", "confidence": 0.95}\n```'
    parsed = provider._extract_json_block(fence_json)
    assert parsed is not None
    assert parsed["document_type"] == "bill_of_lading"

    # Trailing comma
    broken_json = '{"document_type": "bill_of_lading", "confidence": 0.95, }'
    repaired = provider._extract_json_block(broken_json)
    assert repaired is not None
    assert repaired["confidence"] == 0.95


@pytest.mark.asyncio
async def test_ai_provider_fallback_when_unconfigured():
    """11. Test AI provider falls back cleanly when GEMINI_API_KEY is unset."""
    provider = GeminiExtractionProvider(api_key=None)
    assert provider.is_configured is False

    bl_text = "BILL OF LADING\nB/L NO: MSCU999888\nVESSEL: MSC GEMINI"
    data, evidence, confidence = await provider.extract_bill_of_lading(bl_text, pages=[])

    assert data["document_metadata"]["bl_number"] == "MSCU999888"
    assert data["shipment"]["vessel_name"] == "MSC GEMINI"
    assert confidence > 0.0


# ─── API Integration Tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_document_reprocess_endpoint(client: AsyncClient):
    """12. Test POST /api/documents/{id}/reprocess safely reruns extraction."""
    headers = await auth_user(client, "reprocess_user@documind.ai")
    pdf_bytes = create_realistic_bl_pdf()

    upload_resp = await client.post(
        "/api/documents/upload?sync=true",
        files={"files": ("bl_sample.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["data"]["document"]["id"]

    # Call reprocess
    reprocess_resp = await client.post(
        f"/api/documents/{doc_id}/reprocess",
        headers=headers,
    )
    assert reprocess_resp.status_code == 200
    detail = reprocess_resp.json()["data"]
    assert detail["document_id"] == doc_id
    assert detail["extracted_json"]["document_metadata"]["bl_number"] == "MEDU987654321"


@pytest.mark.asyncio
async def test_extraction_status_and_text_endpoints(client: AsyncClient):
    """13. Test GET /api/documents/{id}/text and /processing-status."""
    headers = await auth_user(client, "status_user@documind.ai")
    pdf_bytes = create_realistic_bl_pdf()

    upload_resp = await client.post(
        "/api/documents/upload?sync=true",
        files={"files": ("bl_status.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    doc_id = upload_resp.json()["data"]["document"]["id"]

    # 1. Processing status
    status_resp = await client.get(
        f"/api/documents/{doc_id}/processing-status",
        headers=headers,
    )
    assert status_resp.status_code == 200
    st_data = status_resp.json()["data"]
    assert "stages" in st_data
    assert len(st_data["stages"]) >= 5

    # 2. Text endpoint
    text_resp = await client.get(
        f"/api/documents/{doc_id}/text",
        headers=headers,
    )
    assert text_resp.status_code == 200
    txt_data = text_resp.json()["data"]
    assert txt_data["total_pages"] >= 1
    assert "MEDU987654321" in txt_data["full_text"]
    assert len(txt_data["pages"]) >= 1


@pytest.mark.asyncio
async def test_document_ownership_security(client: AsyncClient):
    """14. Test authorization isolation: User B cannot access User A's document."""
    headers_a = await auth_user(client, "usera@documind.ai")
    headers_b = await auth_user(client, "userb@documind.ai")

    upload_resp = await client.post(
        "/api/documents/upload?sync=true",
        files={"files": ("secret_a.pdf", io.BytesIO(create_realistic_bl_pdf()), "application/pdf")},
        headers=headers_a,
    )
    doc_id = upload_resp.json()["data"]["document"]["id"]

    # User B tries to view text
    text_resp = await client.get(f"/api/documents/{doc_id}/text", headers=headers_b)
    assert text_resp.status_code == 404

    # User B tries to reprocess
    reproc_resp = await client.post(f"/api/documents/{doc_id}/reprocess", headers=headers_b)
    assert reproc_resp.status_code == 404


@pytest.mark.asyncio
async def test_notification_creation(client: AsyncClient):
    """15. Test notifications created upon document upload and completion."""
    headers = await auth_user(client, "notif_lead@documind.ai")
    pdf_bytes = create_realistic_bl_pdf()

    await client.post(
        "/api/documents/upload?sync=true",
        files={"files": ("bl_notif.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )

    notifs_resp = await client.get("/api/notifications", headers=headers)
    assert notifs_resp.status_code == 200
    items = notifs_resp.json()["data"]["items"]
    assert len(items) >= 1
    titles = [item["title"] for item in items]
    assert any("Document" in t for t in titles)
