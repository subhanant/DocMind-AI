"""
AI Extraction Provider Abstraction.

Defines the interface for AI classification and extraction providers.
Ensures the rest of the application remains completely decoupled from specific AI models/SDKs.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

from app.schemas.extraction import (
    BillOfLadingExtraction,
    DocumentClassificationResult,
)


class AIExtractionProvider(ABC):
    """
    Abstract interface for AI document intelligence providers.
    All providers (Gemini, Claude, GPT, Local/Heuristic) must implement these methods.
    """

    @abstractmethod
    async def classify_document(
        self,
        text: str,
        pages: list[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
    ) -> DocumentClassificationResult:
        """
        Classifies the document into one of the supported document types.
        Returns document_type, confidence (0.0 - 1.0), and human-readable reason.
        """
        ...

    @abstractmethod
    async def extract_bill_of_lading(
        self,
        text: str,
        pages: list[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
    ) -> Tuple[dict[str, Any], dict[str, Any], float]:
        """
        Extracts all 27 priority Bill of Lading fields with field-level confidence.
        
        Returns:
            (extracted_json, field_evidence_map, overall_confidence)
        """
        ...

    def validate_extraction(
        self, extracted_data: dict[str, Any], schema_class: Any = BillOfLadingExtraction
    ) -> Tuple[bool, list[str]]:
        """
        Validates extraction payload against the target Pydantic schema.
        Returns (is_valid, list_of_error_messages).
        """
        try:
            schema_class.model_validate(extracted_data)
            return True, []
        except Exception as e:
            return False, [str(e)]
