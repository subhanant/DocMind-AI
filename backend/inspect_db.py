import sqlite3, json

conn = sqlite3.connect('documind.db')
c = conn.cursor()

# Full extraction JSON for the completed docs
c.execute("SELECT er.document_id, er.extracted_json, er.confidence_score FROM extraction_results er ORDER BY er.created_at DESC LIMIT 3")
rows = c.fetchall()
print("=== EXTRACTION RESULTS (full JSON) ===")
for r in rows:
    print(f"\nDOC_ID: {r[0]}")
    print(f"Confidence: {r[2]}")
    if r[1]:
        j = json.loads(r[1])
        print(f"JSON keys: {list(j.keys())}")
        print(f"Full JSON: {json.dumps(j, indent=2)[:2000]}")
    else:
        print("extracted_json: NULL")

# Full document data
c.execute("SELECT d.id, d.original_filename, d.file_type, d.mime_type, d.document_type, d.processing_status, d.extraction_confidence, d.storage_path FROM documents d ORDER BY d.created_at DESC LIMIT 5")
rows = c.fetchall()
print("\n\n=== DOCUMENTS (full) ===")
for r in rows:
    print(f"\n  ID: {r[0]}")
    print(f"  filename: {r[1]}")
    print(f"  file_type: {r[2]} | mime: {r[3]}")
    print(f"  doc_type: {r[4]} | status: {r[5]} | conf: {r[6]}")
    print(f"  storage_path: {r[7]}")

conn.close()
