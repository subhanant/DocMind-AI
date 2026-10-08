"""
Tests for Document Classification, Structured Extraction, and Extraction Endpoints.
"""
import io
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import pymupdf
from app.db.database import Base, get_db
from app.db.models.document import DocumentStatus, DocumentType
from app.main import app
from app.services.bill_of_lading_extractor import BillOfLadingRuleExtractor
from app.services.classifier_service import DocumentClassifierService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

SAMPLE_BL_TEXT = """
OCEAN BILL OF LADING
B/L NO: MSCU9283741
BOOKING NO: BKG-2026-8891
CARRIER: MSC

SHIPPER:
ACME GLOBAL EXPORTS LTD
123 HARBOR BLVD, SUITE 400
SHANGHAI, CHINA
TEL: +86-21-5555-1234
EMAIL: export@acmeglobal.com

CONSIGNEE:
PACIFIC LOGISTICS INC
789 OCEAN AVENUE
LONG BEACH, CA 90802, USA
TEL: +1-562-555-9876

NOTIFY PARTY:
PACIFIC CUSTOMS BROKERAGE
456 TERMINAL WAY
LONG BEACH, CA 90802, USA

OCEAN VESSEL: MSC OSCAR
VOYAGE NO: 045W
PORT OF LOADING: SHANGHAI
PORT OF DISCHARGE: LONG BEACH
PLACE OF DELIVERY: LOS ANGELES, CA

SHIPPED ON BOARD DATE: 2026-05-12
B/L DATE: 2026-05-10
PLACE OF ISSUE: SHANGHAI

DESCRIPTION OF GOODS:
INDUSTRIAL ELECTRIC MOTORS AND SPARE PARTS
HS CODE: 8501.52

CONTAINER NO: MSCU1234567
SEAL NO: ML-889901
CONTAINER TYPE: 40' HIGH CUBE
GROSS WEIGHT: 22,450.00 KGS
MEASUREMENT: 58.50 CBM
NO. OF PACKAGES: 450 CARTONS

FREIGHT PREPAID
CURRENCY: USD
MARKS & NUMBERS: ACME/LA/2026/01-450

DANGEROUS GOODS: UN1993 IMO CLASS 3.1
"""


@pytest_asyncio.fixture(scope="module")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncSession:
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def test_classifier_service():
    doc_type, conf = DocumentClassifierService.classify(SAMPLE_BL_TEXT, "bill_of_lading.pdf")
    assert doc_type == DocumentType.BILL_OF_LADING
    assert conf >= 0.8

    inv_text = "COMMERCIAL INVOICE\nInvoice No: INV-1002\nUnit Price: $500\nTotal Amount: $10,000"
    doc_type2, conf2 = DocumentClassifierService.classify(inv_text, "invoice.pdf")
    assert doc_type2 == DocumentType.COMMERCIAL_INVOICE


def test_bill_of_lading_rule_extractor():
    schema, confidence = BillOfLadingRuleExtractor.extract(SAMPLE_BL_TEXT)

    assert schema.bl_number is not None
    assert schema.bl_number.value == "MSCU9283741"
    assert schema.booking_number.value == "BKG-2026-8891"
    assert schema.shipping_line.value == "MSC"
    assert schema.vessel_name.value == "MSC OSCAR"
    assert schema.voyage_number.value == "045W"
    assert schema.port_of_loading.value == "SHANGHAI"
    assert schema.port_of_discharge.value == "LONG BEACH"
    assert schema.shipper.name.value == "ACME GLOBAL EXPORTS LTD"
    assert "CHINA" in schema.shipper.address.value
    assert schema.consignee.name.value == "PACIFIC LOGISTICS INC"
    assert schema.freight_terms.value == "Prepaid"
    assert schema.hs_code.value == "8501.52"

    assert schema.containers is not None
    assert len(schema.containers) >= 1
    assert schema.containers[0].container_number.value == "MSCU1234567"
    assert schema.containers[0].seal_number.value == "ML-889901"

    assert schema.dangerous_goods is not None
    assert schema.dangerous_goods.un_number.value == "UN1993"
    assert schema.dangerous_goods.imo_class.value == "3.1"

    assert confidence >= 0.80


@pytest.mark.asyncio
async def test_end_to_end_upload_and_extraction(client: AsyncClient):
    # Register & Login
    unique_email = f"extractor_{uuid.uuid4().hex[:6]}@example.com"
    reg_resp = await client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "SecurePassword123!", "full_name": "Logistics Pro"},
    )
    assert reg_resp.status_code == 201

    login_resp = await client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a synthetic PDF containing Bill of Lading data
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), SAMPLE_BL_TEXT)
    pdf_bytes = doc.tobytes()
    doc.close()

    # Upload PDF
    upload_resp = await client.post(
        "/api/documents/upload?sync=true",
        headers=headers,
        files=[("files", ("BOL_MSCU9283741.pdf", pdf_bytes, "application/pdf"))],
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()["data"]["document"]
    doc_id = doc_data["id"]

    assert doc_data["document_type"] == "bill_of_lading"
    assert doc_data["processing_status"] in ["completed", "needs_review"]
    assert doc_data["extraction_confidence"] is not None

    # Fetch extraction details
    ext_resp = await client.get(f"/api/documents/{doc_id}/extraction", headers=headers)
    assert ext_resp.status_code == 200
    ext_data = ext_resp.json()["data"]
    assert ext_data["extracted_json"] is not None
    assert ext_data["extracted_json"]["document_metadata"]["bl_number"] == "MSCU9283741"
    assert ext_data["extracted_json"]["shipment"]["vessel_name"] == "MSC OSCAR"

    # Update/edit extraction data (human review)
    updated_payload = ext_data["extracted_json"]
    updated_payload["document_metadata"]["bl_number"] = "MSCU-VERIFIED-999"

    put_resp = await client.put(
        f"/api/documents/{doc_id}/extraction",
        headers=headers,
        json=updated_payload,
    )
    assert put_resp.status_code == 200
    updated_ext = put_resp.json()["data"]
    assert updated_ext["extracted_json"]["document_metadata"]["bl_number"] == "MSCU-VERIFIED-999"

    # Stream/preview original file
    file_resp = await client.get(f"/api/documents/{doc_id}/file", headers=headers)
    assert file_resp.status_code == 200
    assert file_resp.content == pdf_bytes

    # Reprocess document
    reprocess_resp = await client.post(f"/api/documents/{doc_id}/reprocess", headers=headers)
    assert reprocess_resp.status_code == 200
    reprocessed_data = reprocess_resp.json()["data"]
    assert reprocessed_data["extracted_json"]["document_metadata"]["bl_number"] == "MSCU9283741"
