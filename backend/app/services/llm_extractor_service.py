"""
LLM and Hybrid AI Document Extraction Service (Phase 4).

Extracts structured data from document text using:
1. LLM API (OpenAI / Gemini / Anthropic if configured)
2. High-precision rule & NLP extraction engine (as default or fallback)
"""
import json
import os
import re
from typing import Any, Dict, Optional, Tuple

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.document import DocumentType
from app.schemas.extraction import BillOfLadingSchema
from app.services.bill_of_lading_extractor import BillOfLadingRuleExtractor

settings = get_settings()
logger = get_logger(__name__)


class LLMExtractorService:
    """Hybrid AI extraction service supporting LLMs and deterministic pattern extraction."""

    @classmethod
    async def extract_bill_of_lading(
        cls,
        text: str,
        filename: str = "",
        document_type: DocumentType = DocumentType.BILL_OF_LADING,
    ) -> Tuple[Dict[str, Any], float]:
        """
        Extract Bill of Lading data and return (extracted_dict, confidence_score).
        """
        if not text:
            return {}, 0.0

        api_key = settings.AI_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")

        # If LLM API key configured, attempt LLM extraction
        if api_key:
            try:
                llm_result, llm_conf = await cls._extract_with_llm(text, api_key)
                if llm_result:
                    return llm_result, llm_conf
            except Exception as e:
                logger.warning("LLM API extraction failed, falling back to pattern extractor", error=str(e))

        # Built-in high-fidelity pattern & NLP extractor
        schema_obj, confidence = BillOfLadingRuleExtractor.extract(text)
        extracted_dict = schema_obj.model_dump(exclude_none=True)
        return extracted_dict, confidence

    @classmethod
    async def _extract_with_llm(cls, text: str, api_key: str) -> Tuple[Dict[str, Any], float]:
        """Extract using OpenAI or compatible JSON completion API."""
        prompt = (
            "You are an expert maritime shipping and Bill of Lading document intelligence parser.\n"
            "Extract structured data from the following Bill of Lading document text into the exact JSON schema.\n"
            "Wrap every extracted field in an object with `value`, `confidence` (0.0 to 1.0), and `source_text`.\n"
            "Schema includes:\n"
            "- bl_number, bl_type, bl_status, bl_date, place_of_issue\n"
            "- shipper (name, address, country, contact_phone, contact_email)\n"
            "- consignee (name, address, country, contact_phone, contact_email)\n"
            "- notify_party (name, address, country)\n"
            "- shipping_line, carrier, vessel_name, voyage_number\n"
            "- port_of_loading, port_of_discharge, place_of_delivery, place_of_receipt\n"
            "- description, gross_weight, net_weight, volume, number_of_packages, hs_code\n"
            "- containers (list of container_number, seal_number, container_type, gross_weight)\n"
            "- freight_terms (Prepaid/Collect), freight_currency\n"
            "Return valid JSON only without markdown codeblocks.\n\n"
            f"DOCUMENT TEXT:\n{text[:8000]}"
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.AI_MODEL or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You extract structured data from shipping documents as JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed_json = json.loads(content)
                return parsed_json, 0.95

        return {}, 0.0
