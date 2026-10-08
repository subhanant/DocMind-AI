"""
Verification script testing DocumentVisionPipeline on BL2.pdf.
"""
import asyncio
import json
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath("."))

from app.services.vision.document_vision_pipeline import DocumentVisionPipeline


async def main():
    test_pdf_path = "storage/2471d668-02c3-49a4-aba1-da4badd34b73/2026/10/b962e948e4dc4f9c8f81681aa9b96f47.pdf"
    if not os.path.exists(test_pdf_path):
        print(f"File not found: {test_pdf_path}")
        return

    with open(test_pdf_path, "rb") as f:
        file_bytes = f.read()

    pipeline = DocumentVisionPipeline()
    output = await pipeline.process_document(
        file_bytes=file_bytes,
        mime_type="application/pdf",
        filename="BL2.pdf",
    )

    print("\n" + "=" * 60)
    print("DOCUMENT VISION PIPELINE VERIFICATION RESULTS (BL2.pdf)")
    print("=" * 60)

    bl_field = output.fields_27.get("bill_of_lading_number", {})
    print(f"\n1. B/L NUMBER RESULT:")
    print(f"   Value Verbatim:    '{bl_field.get('value_verbatim')}'")
    print(f"   Value Normalized:  '{bl_field.get('value_normalized')}'")
    print(f"   Confidence:        {bl_field.get('confidence')}")
    print(f"   Validation Status: '{bl_field.get('validation_status')}'")
    print(f"   Source Page:       {bl_field.get('source_page')}")
    print(f"   Source BBox:       {bl_field.get('source_bbox')}")
    print(f"   Extraction Method: '{bl_field.get('extraction_method')}'")

    print(f"\n2. OTHER 27 CORE FIELDS POPULATED:")
    for k, v in output.fields_27.items():
        if v.get("value_verbatim"):
            print(f"   {k:25}: {v.get('value_verbatim')[:35]} (conf: {v.get('confidence')})")

    print(f"\n3. MULTI-CONTAINER RECORDS PRESERVED ({len(output.containers)} found):")
    for i, c in enumerate(output.containers):
        c_num = c.get("container_number", {}).get("value_verbatim")
        c_seal = c.get("seal_number", {}).get("value_verbatim")
        c_type = c.get("container_type", {}).get("value_verbatim")
        c_wt = c.get("gross_cargo_weight", {}).get("value_verbatim")
        print(f"   Row {i+1}: {c_num} | Seal: {c_seal} | Type: {c_type} | Weight: {c_wt}")

    print(f"\n4. AUDIT REPORT:")
    print(f"   Passed Checks: {output.audit_report.passed_checks}/{output.audit_report.total_checks}")
    print(f"   Is Valid:      {output.audit_report.is_valid}")
    for chk in output.audit_report.checks:
        status_icon = "PASS" if chk.passed else "FAIL"
        print(f"   [{status_icon}] {chk.check_name}: {chk.details}")

    print(f"\n5. DEBUG ANNOTATION CACHED:")
    print(f"   Cached Pages: {list(output.debug_annotation_cache.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
