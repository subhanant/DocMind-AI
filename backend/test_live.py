"""
Live API test - reprocess document and verify extraction result.
"""
import asyncio
import json
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./documind.db")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def main():
    from app.core.config import get_settings
    from app.services import ai as ai_services

    settings = get_settings()
    print(f"Model: {settings.AI_MODEL}")
    print(f"Gemini API key set: {bool(settings.GEMINI_API_KEY)}")

    # Reset singleton
    ai_services._default_ai_provider = None

    from app.db.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.db.models.document import Document

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(Document.storage_path != None).limit(3)
        )
        docs = result.scalars().all()

        for doc in docs:
            print(f"\n{'='*60}")
            print(f"Testing: {doc.original_filename} ({doc.mime_type})")
            print(f"  Current type: {doc.document_type}, status: {doc.processing_status}")

            from app.services.storage_service import get_storage_service
            storage = get_storage_service()
            try:
                file_bytes = await storage.get(doc.storage_path)
            except Exception as e:
                print(f"  Cannot read file: {e}")
                continue

            from app.services.text_extraction_service import DocumentTextExtractor
            extractor = DocumentTextExtractor()
            pages_res = extractor.extract_pages(file_bytes, doc.original_filename, doc.mime_type)
            print(f"  Text chars: {pages_res.total_chars}, OCR: {pages_res.ocr_used}")

            from app.services.ai import get_ai_provider
            ai = get_ai_provider()
            print(f"  AI provider: {ai.__class__.__name__}, configured: {ai.is_configured}")

            # Try classification with image bytes
            is_image = (doc.mime_type or "").startswith("image/")
            meta = {"filename": doc.original_filename, "size": doc.file_size}
            if is_image or pages_res.is_scanned:
                meta["image_bytes"] = file_bytes
                print(f"  Passing image_bytes for {'image' if is_image else 'scanned'} document")

            classification = await ai.classify_document(
                text=pages_res.full_text,
                pages=[p.to_dict() for p in pages_res.pages],
                metadata=meta,
            )
            print(f"  Classified as: {classification.document_type} ({classification.confidence:.0%})")
            print(f"  Reason: {classification.reason}")

            if classification.document_type == "bill_of_lading":
                print("\n  Running BL extraction...")
                data, evidence, confidence = await ai.extract_bill_of_lading(
                    text=pages_res.full_text,
                    pages=[p.to_dict() for p in pages_res.pages],
                    metadata=meta,
                )
                print(f"  Extraction confidence: {confidence}")
                print(f"  Extracted keys: {list(data.keys())}")

                meta_data = data.get("document_metadata", {})
                print(f"  BL Number: {meta_data.get('bl_number')}")
                print(f"  BL Date: {meta_data.get('bl_date')}")

                shipment = data.get("shipment", {})
                print(f"  Carrier: {shipment.get('carrier')}")
                print(f"  Vessel: {shipment.get('vessel_name')}")
                print(f"  POL: {shipment.get('port_of_loading')}")
                print(f"  POD: {shipment.get('port_of_discharge')}")

                containers = data.get("containers", [])
                print(f"  Containers: {len(containers)}")
                if containers:
                    print(f"  First container: {containers[0].get('container_number')}")

                print(f"\n  FULL DATA:\n{json.dumps(data, indent=2)[:2000]}")
            else:
                print(f"  Not a BL document — skipping extraction")


asyncio.run(main())
