"""
Document Schema Registry.

Maintains the mapping between Document Types and their extraction schemas/capabilities.
Phase 2 mandates full implementation for Bill of Lading.
Other document types are registered, allowing classification while reporting:
"Extraction schema not implemented yet."
"""
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel

from app.db.models.document import DocumentType
from app.schemas.extraction import BillOfLadingExtraction


class DocumentSchemaRegistry:
    """Registry mapping document types to Pydantic schemas and capability flags."""

    _registry: Dict[str, Dict[str, Any]] = {
        DocumentType.BILL_OF_LADING.value: {
            "schema": BillOfLadingExtraction,
            "version": "2.0",
            "is_implemented": True,
            "display_name": "Bill of Lading",
            "description": "Ocean and multimodal shipping bill of lading",
        },
        DocumentType.COMMERCIAL_INVOICE.value: {
            "schema": None,
            "version": "1.0",
            "is_implemented": False,
            "display_name": "Commercial Invoice",
            "description": "Trade and sales commercial invoice",
        },
        DocumentType.PACKING_LIST.value: {
            "schema": None,
            "version": "1.0",
            "is_implemented": False,
            "display_name": "Packing List",
            "description": "Detailed cargo packaging specification",
        },
        DocumentType.PURCHASE_ORDER.value: {
            "schema": None,
            "version": "1.0",
            "is_implemented": False,
            "display_name": "Purchase Order",
            "description": "Procurement purchase order",
        },
        DocumentType.CERTIFICATE_OF_ORIGIN.value: {
            "schema": None,
            "version": "1.0",
            "is_implemented": False,
            "display_name": "Certificate of Origin",
            "description": "Chamber of commerce origin certificate",
        },
        DocumentType.DELIVERY_CHALLAN.value: {
            "schema": None,
            "version": "1.0",
            "is_implemented": False,
            "display_name": "Delivery Challan",
            "description": "Goods dispatch note",
        },
        DocumentType.CONTRACT.value: {
            "schema": None,
            "version": "1.0",
            "is_implemented": False,
            "display_name": "Contract / Agreement",
            "description": "Legal contract or terms agreement",
        },
        DocumentType.RECEIPT.value: {
            "schema": None,
            "version": "1.0",
            "is_implemented": False,
            "display_name": "Payment Receipt",
            "description": "Proof of payment receipt",
        },
        DocumentType.CUSTOMS_DOCUMENT.value: {
            "schema": None,
            "version": "1.0",
            "is_implemented": False,
            "display_name": "Customs Document",
            "description": "Customs clearance declaration or bill of entry",
        },
        DocumentType.SHIPPING_DOCUMENT.value: {
            "schema": None,
            "version": "1.0",
            "is_implemented": False,
            "display_name": "General Shipping Document",
            "description": "Shipping instructions or mates receipt",
        },
        DocumentType.GENERAL_DOCUMENT.value: {
            "schema": None,
            "version": "1.0",
            "is_implemented": False,
            "display_name": "General Document",
            "description": "Uncategorized business document",
        },
        DocumentType.UNKNOWN.value: {
            "schema": None,
            "version": "1.0",
            "is_implemented": False,
            "display_name": "Unknown",
            "description": "Unrecognized document format",
        },
    }

    @classmethod
    def is_implemented(cls, document_type: str) -> bool:
        """Check if extraction schema is implemented for this type."""
        entry = cls._registry.get(document_type)
        return bool(entry and entry.get("is_implemented"))

    @classmethod
    def get_schema(cls, document_type: str) -> Optional[Type[BaseModel]]:
        """Return target Pydantic schema for document type."""
        entry = cls._registry.get(document_type)
        if entry:
            return entry.get("schema")
        return None

    @classmethod
    def get_schema_version(cls, document_type: str) -> str:
        entry = cls._registry.get(document_type)
        if entry:
            return entry.get("version", "1.0")
        return "1.0"

    @classmethod
    def get_unimplemented_message(cls, document_type: str) -> str:
        return f"Extraction schema not implemented yet for document type '{document_type}'."
