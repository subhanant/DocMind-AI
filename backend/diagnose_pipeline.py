"""
Comprehensive pipeline diagnostic script.
Runs the full pipeline on the first uploaded image/document in storage
and prints each stage result to identify where extraction fails.
"""
import asyncio
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./documind.db")


async def main():
    from app.core.config import get_settings
    settings = get_settings()
    print(f"GEMINI_API_KEY set: {bool(settings.GEMINI_API_KEY)}")
    print(f"AI_MODEL: {settings.AI_MODEL}")
    print(f"OCR_ENABLED: {settings.OCR_ENABLED}")

    # Check tesseract
    import shutil
    tess = shutil.which("tesseract")
    print(f"Tesseract binary on PATH: {tess}")

    # Find a stored file
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import select, text
    from app.db.models.document import Document

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(Document.storage_path != None).limit(3)
        )
        docs = result.scalars().all()
        if not docs:
            print("No documents found in DB")
            return

        for doc in docs:
            print(f"\n{'='*60}")
            print(f"Document: {doc.original_filename} | type: {doc.document_type} | status: {doc.processing_status}")
            print(f"Storage path: {doc.storage_path}")

            # Try to read file
            from app.services.storage_service import get_storage_service
            storage = get_storage_service()
            try:
                file_bytes = await storage.get(doc.storage_path)
                print(f"File size: {len(file_bytes)} bytes")
            except Exception as e:
                print(f"CANNOT READ FILE: {e}")
                continue

            # Run OCR
            print("\n--- OCR Stage ---")
            from app.services.text_extraction_service import DocumentTextExtractor
            extractor = DocumentTextExtractor()
            try:
                pages_result = extractor.extract_pages(file_bytes, doc.original_filename, doc.mime_type)
                print(f"Total pages: {pages_result.total_pages}")
                print(f"Total chars: {pages_result.total_chars}")
                print(f"OCR used: {pages_result.ocr_used}")
                print(f"Extractor: {pages_result.extractor_used}")
                print(f"Text preview (first 500 chars): {pages_result.full_text[:500]!r}")
            except Exception as e:
                print(f"OCR FAILED: {e}")
                import traceback; traceback.print_exc()
                continue

            if not pages_result.full_text.strip():
                print("WARNING: OCR returned empty text!")
                continue

            # Run classification
            print("\n--- Classification Stage ---")
            from app.services.ai import get_ai_provider
            ai = get_ai_provider()
            try:
                classification = await ai.classify_document(
                    text=pages_result.full_text,
                    pages=[p.to_dict() for p in pages_result.pages],
                    metadata={"filename": doc.original_filename},
                )
                print(f"Document type: {classification.document_type}")
                print(f"Confidence: {classification.confidence}")
                print(f"Reason: {classification.reason}")
            except Exception as e:
                print(f"CLASSIFICATION FAILED: {e}")
                import traceback; traceback.print_exc()
                continue

            if classification.document_type != "bill_of_lading":
                print(f"Classified as {classification.document_type}, skipping BL extraction")
                continue

            # Run BL extraction
            print("\n--- BL Extraction Stage ---")
            try:
                data, evidence, confidence = await ai.extract_bill_of_lading(
                    text=pages_result.full_text,
                    pages=[p.to_dict() for p in pages_result.pages],
                    metadata={"filename": doc.original_filename},
                )
                print(f"Extraction confidence: {confidence}")
                print(f"Extracted data keys: {list(data.keys())}")
                print(f"document_metadata: {data.get('document_metadata')}")
                print(f"shipment: {data.get('shipment')}")
                print(f"containers count: {len(data.get('containers', []))}")
                print(f"Field evidence keys: {list(evidence.keys())[:10]}")
                print(f"\nFull extracted JSON:\n{json.dumps(data, indent=2)[:3000]}")
            except Exception as e:
                print(f"BL EXTRACTION FAILED: {e}")
                import traceback; traceback.print_exc()


asyncio.run(main())
