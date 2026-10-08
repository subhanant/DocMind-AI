"""
Trigger reprocess for the JPEG documents, verify DB result.
"""
import asyncio, json, sys, os, uuid
sys.path.insert(0, '.')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./documind.db")

TARGET_DOCS = [
    "0bfa3527-6704-4d1b-a823-b864e51142d7",  # WhatsApp JPEG #1
    "e4d33ed8-4970-4ed0-93b5-da69a27581a5",  # WhatsApp JPEG #2
]

async def main():
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.db.models.document import Document, ExtractionResult
    from app.services import ai as ai_services

    for doc_id_str in TARGET_DOCS:
        doc_id = uuid.UUID(doc_id_str)
        print(f"\n{'='*60}")
        print(f"Processing: {doc_id_str}")

        async with AsyncSessionLocal() as db:
            doc_result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = doc_result.scalar_one_or_none()
            if not doc:
                print("  Document not found!")
                continue

            print(f"  File: {doc.original_filename}")
            user_id = doc.user_id

            # Reset AI singleton so fresh settings are loaded
            ai_services._default_ai_provider = None

            from app.api.routes.documents import execute_pipeline_for_document
            print("  Running pipeline (this may take 30-90s)...")
            await execute_pipeline_for_document(doc_id, user_id, db)

        # Re-open session to read fresh state
        async with AsyncSessionLocal() as db2:
            doc_result2 = await db2.execute(select(Document).where(Document.id == doc_id))
            doc2 = doc_result2.scalar_one_or_none()
            print(f"  Status: {doc2.processing_status}")
            print(f"  Type: {doc2.document_type}")
            print(f"  Confidence: {doc2.extraction_confidence}")

            er_result = await db2.execute(
                select(ExtractionResult).where(ExtractionResult.document_id == doc_id)
            )
            er = er_result.scalar_one_or_none()
            if er:
                raw = er.extracted_json
                if isinstance(raw, str):
                    j = json.loads(raw)
                elif isinstance(raw, dict):
                    j = raw
                else:
                    j = {}
                print(f"  extracted_json keys: {list(j.keys())}")
                meta = j.get("document_metadata", {})
                print(f"  BL Number : {meta.get('bl_number')}")
                print(f"  BL Date   : {meta.get('bl_date')}")
                ship = j.get("shipment", {})
                print(f"  Carrier   : {ship.get('carrier')}")
                print(f"  POL/POD   : {ship.get('port_of_loading')} / {ship.get('port_of_discharge')}")
                ctrs = j.get("containers", [])
                print(f"  Containers: {len(ctrs)}")
                if ctrs:
                    print(f"  Ctr #1    : {ctrs[0].get('container_number')}")
                print(f"  SUCCESS: Extraction data is in DB!")
            else:
                print("  FAIL: No ExtractionResult record in DB!")

asyncio.run(main())
