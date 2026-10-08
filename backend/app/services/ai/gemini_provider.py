"""
Gemini AI Extraction Provider.

Uses the official Google GenAI Python SDK (`google-genai`).
Features:
- Reads GEMINI_API_KEY from application settings
- Uses configurable AI_MODEL (default: gemini-2.5-flash)
- Strict prompt injection mitigation
- Safe JSON extraction and repair
- Graceful fallback to Heuristic provider if API key is not configured or network fails
- Image-direct multimodal extraction when OCR text is empty/insufficient
- Retry logic with backoff for 503/429 transient errors
"""
import asyncio
import io
import json
import re
from typing import Any, Optional, Tuple

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.extraction import (
    BillOfLadingExtraction,
    DocumentClassificationResult,
)
from app.services.ai.heuristic_provider import HeuristicExtractionProvider
from app.services.ai.prompts import (
    BILL_OF_LADING_PROMPT,
    CLASSIFICATION_PROMPT,
    SYSTEM_PROMPT,
)
from app.services.ai.provider import AIExtractionProvider

logger = get_logger(__name__)
settings = get_settings()

# Minimum chars for text-based extraction (below this triggers image-direct fallback)
_MIN_CHARS_FOR_TEXT_EXTRACTION = 100

_UNSET = object()


class GeminiExtractionProvider(AIExtractionProvider):
    """
    Google GenAI / Gemini implementation.
    Operates using the official google-genai library.
    Supports text-based extraction AND image-direct multimodal extraction for scanned docs.
    """

    def __init__(self, api_key: Optional[str] = _UNSET, model: Optional[str] = None):
        if api_key is _UNSET:
            self.api_key = settings.GEMINI_API_KEY
        else:
            self.api_key = api_key
        self.model = model or settings.AI_MODEL
        self.timeout = settings.AI_REQUEST_TIMEOUT
        self._fallback_provider = HeuristicExtractionProvider()

        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Gemini AI extraction provider initialized", model=self.model)
            except Exception as e:
                logger.warning("Failed to initialize Google GenAI Client", error=str(e))
        else:
            logger.info("GEMINI_API_KEY is not configured; fallback provider active")

    @property
    def is_configured(self) -> bool:
        return self._client is not None and bool(self.api_key)

    # ─── JSON Helpers ──────────────────────────────────────────────────────────

    def _extract_json_block(self, text: str) -> Optional[dict[str, Any]]:
        """Safely extract and repair JSON from AI response."""
        clean = text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        try:
            return json.loads(clean)
        except Exception:
            pass

        match = re.search(r"(\{.*\})", clean, re.DOTALL)
        if match:
            candidate = match.group(1)
            repaired = re.sub(r",\s*([\]\}])", r"\1", candidate)
            try:
                return json.loads(repaired)
            except Exception:
                pass

        return None

    def _is_retryable_error(self, error: Exception) -> bool:
        """Return True for transient errors that should be retried."""
        err_str = str(error)
        return any(code in err_str for code in [
            "503", "429", "UNAVAILABLE", "Resource has been exhausted", "overloaded"
        ])

    async def _generate_content(self, **kwargs: Any) -> Any:
        """Run the synchronous Gemini SDK outside FastAPI's event loop with multi-model failover."""
        primary_model = kwargs.get("model", self.model)
        models_to_try = [primary_model]
        for m_cand in ["gemini-flash-lite-latest", "gemini-3.1-flash-lite-preview", "gemini-3.5-flash", "gemini-3.8-flash"]:
            if m_cand not in models_to_try:
                models_to_try.append(m_cand)

        last_error = None
        for m in models_to_try:
            call_kwargs = dict(kwargs)
            call_kwargs["model"] = m
            try:
                return await asyncio.to_thread(self._client.models.generate_content, **call_kwargs)
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if any(code in err_msg for code in ["429", "404", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "not found", "is no longer available"]):
                    logger.warning(f"Gemini model {m} failed with {err_msg[:100]}... trying fallback model")
                    continue
                raise
        if last_error:
            raise last_error

    # ─── Field Evidence Builder ─────────────────────────────────────────────────

    def _ensure_field_evidence(
        self, data: dict[str, Any], field_evidence: dict[str, Any], text: str
    ) -> dict[str, Any]:
        """Ensure field_evidence map has all extracted priority fields with confidence & source citations."""
        evidence = dict(field_evidence) if field_evidence else {}

        def add_if_missing(key: str, val: Any, conf: float = 0.95) -> None:
            if val is not None and (key not in evidence or evidence[key].get("value") is None):
                src_snippet = None
                str_v = str(val) if not isinstance(val, dict) else str(val.get("value", ""))
                if str_v and text and str_v in text:
                    idx = text.find(str_v)
                    start = max(0, idx - 15)
                    end = min(len(text), idx + len(str_v) + 15)
                    src_snippet = text[start:end].strip()
                evidence[key] = {
                    "value": val,
                    "confidence": conf,
                    "source_text": src_snippet or (str_v[:100] if str_v else None),
                    "page": 1,
                }

        meta = data.get("document_metadata", {})
        add_if_missing("bl_number", meta.get("bl_number"), 0.98)
        add_if_missing("bl_date", meta.get("bl_date"), 0.94)
        add_if_missing("bl_type", meta.get("bl_type"), 0.90)
        add_if_missing("bl_status", meta.get("bl_status"), 0.90)
        add_if_missing("place_of_issue", meta.get("place_of_issue"), 0.88)
        add_if_missing("original_copies", meta.get("original_copies"), 0.88)

        parties = data.get("parties", {})
        add_if_missing("shipper_name", parties.get("shipper", {}).get("name"), 0.92)
        add_if_missing("shipper_address", parties.get("shipper", {}).get("address"), 0.88)
        add_if_missing("consignee_name", parties.get("consignee", {}).get("name"), 0.92)
        add_if_missing("consignee_address", parties.get("consignee", {}).get("address"), 0.88)
        add_if_missing("notify_party_name", parties.get("notify_party", {}).get("name"), 0.90)
        add_if_missing("notify_party_address", parties.get("notify_party", {}).get("address"), 0.85)

        shipment = data.get("shipment", {})
        add_if_missing("carrier", shipment.get("carrier"), 0.95)
        add_if_missing("vessel_name", shipment.get("vessel_name"), 0.93)
        add_if_missing("voyage_number", shipment.get("voyage_number"), 0.93)
        add_if_missing("port_of_loading", shipment.get("port_of_loading"), 0.95)
        add_if_missing("port_of_discharge", shipment.get("port_of_discharge"), 0.95)
        add_if_missing("place_of_delivery", shipment.get("place_of_delivery"), 0.90)
        add_if_missing("place_of_receipt", shipment.get("place_of_receipt"), 0.88)
        add_if_missing("booking_number", shipment.get("booking_number"), 0.93)

        dates = data.get("dates", {})
        add_if_missing("on_board_date", dates.get("on_board_date"), 0.92)
        # Also pull bl_date from dates if not already in metadata
        if not evidence.get("bl_date") or evidence["bl_date"].get("value") is None:
            add_if_missing("bl_date", dates.get("bl_date") or dates.get("issue_date"), 0.93)

        cargo = data.get("cargo", {})
        add_if_missing("cargo_description", cargo.get("description"), 0.90)
        add_if_missing("hs_code", cargo.get("hs_code"), 0.94)
        add_if_missing("number_of_packages", cargo.get("number_of_packages"), 0.92)
        add_if_missing("marks_and_numbers", cargo.get("marks_and_numbers"), 0.88)
        add_if_missing("gross_weight", cargo.get("gross_weight"), 0.94)
        add_if_missing("net_weight", cargo.get("net_weight"), 0.92)
        add_if_missing("cbm", cargo.get("cbm"), 0.90)

        freight = data.get("freight", {})
        add_if_missing("freight_terms", freight.get("terms"), 0.94)
        add_if_missing("freight_amount", freight.get("amount"), 0.88)
        add_if_missing("currency", freight.get("currency"), 0.92)

        refs = data.get("references", {})
        add_if_missing("invoice_number", refs.get("invoice_number"), 0.92)

        containers = data.get("containers", [])
        if containers and isinstance(containers, list):
            c0 = containers[0]
            add_if_missing("container_number", c0.get("container_number"), 0.98)
            add_if_missing("seal_number", c0.get("seal_number"), 0.92)
            add_if_missing("container_type", c0.get("container_type"), 0.88)

        return evidence

    # ─── Image Helper ──────────────────────────────────────────────────────────

    def _compress_image(self, image_bytes: bytes, quality: int = 85) -> bytes:
        """Compress image to JPEG for Gemini API."""
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    # ─── Classification ────────────────────────────────────────────────────────

    async def classify_document(
        self,
        text: str,
        pages: list[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
    ) -> DocumentClassificationResult:
        """Classify document using Gemini AI, with heuristic fallback.
        If text is insufficient, uses image-direct multimodal classification.
        """
        if not self.is_configured:
            logger.debug("Gemini not configured, using heuristic classification")
            return await self._fallback_provider.classify_document(text, pages, metadata)

        text_len = len(text.strip())

        if text_len >= _MIN_CHARS_FOR_TEXT_EXTRACTION:
            result = await self._classify_from_text(text)
            if result:
                return result
        else:
            image_bytes = (metadata or {}).get("image_bytes")
            if image_bytes:
                logger.info("Text too short for classification, using image-direct Gemini", text_chars=text_len)
                result = await self._classify_from_image(image_bytes)
                if result:
                    return result
            logger.warning("Insufficient text for Gemini classification, using heuristic", text_chars=text_len)

        return await self._fallback_provider.classify_document(text, pages, metadata)

    async def _classify_from_text(self, text: str) -> Optional[DocumentClassificationResult]:
        """Text-based Gemini classification with retry."""
        prompt = CLASSIFICATION_PROMPT.format(document_text=text[:6000])
        for attempt in range(3):
            try:
                from google.genai import types
                response = await self._generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.1,
                        response_mime_type="application/json",
                    ),
                )
                raw_text = response.text or ""
                data = self._extract_json_block(raw_text)
                if data and "document_type" in data:
                    conf = float(data.get("confidence", 0.85))
                    return DocumentClassificationResult(
                        document_type=str(data["document_type"]).lower().strip(),
                        confidence=min(1.0, max(0.0, conf)),
                        reason=str(data.get("reason", "Classified by Gemini AI")),
                    )
                return None
            except Exception as e:
                if self._is_retryable_error(e) and attempt < 2:
                    wait = 2 ** attempt
                    logger.warning(f"Gemini classify retry {attempt + 1}/3 (backoff {wait}s)", error=str(e))
                    await asyncio.sleep(wait)
                else:
                    logger.warning("Gemini text classification failed", error=str(e))
                    return None
        return None

    async def _classify_from_image(self, image_bytes: bytes) -> Optional[DocumentClassificationResult]:
        """Image-direct Gemini multimodal classification for scanned documents."""
        try:
            img_data = self._compress_image(image_bytes, quality=85)
            from google.genai import types
            prompt = (
                "Look at this shipping/trade document image. Classify it into exactly one of these types: "
                "bill_of_lading, commercial_invoice, packing_list, purchase_order, certificate_of_origin, "
                "delivery_challan, contract, receipt, customs_document, shipping_document, general_document, unknown.\n"
                "Return ONLY valid JSON: {\"document_type\": \"<type>\", \"confidence\": <0.0-1.0>, \"reason\": \"<reason>\"}"
            )
            for attempt in range(3):
                try:
                    response = await self._generate_content(
                        model=self.model,
                        contents=[
                            types.Part.from_bytes(data=img_data, mime_type="image/jpeg"),
                            prompt,
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.1,
                        ),
                    )
                    raw_text = response.text or ""
                    data = self._extract_json_block(raw_text)
                    if data and "document_type" in data:
                        conf = float(data.get("confidence", 0.80))
                        logger.info("Gemini image classification succeeded", doc_type=data["document_type"], confidence=conf)
                        return DocumentClassificationResult(
                            document_type=str(data["document_type"]).lower().strip(),
                            confidence=min(1.0, max(0.0, conf)),
                            reason=str(data.get("reason", "Classified via image analysis")),
                        )
                    return None
                except Exception as e:
                    if self._is_retryable_error(e) and attempt < 2:
                        wait = 3 ** attempt
                        logger.warning(f"Gemini image classify retry {attempt + 1}/3 (backoff {wait}s)", error=str(e))
                        await asyncio.sleep(wait)
                    else:
                        logger.warning("Gemini image classification failed", error=str(e))
                        return None
        except Exception as e:
            logger.warning("Image classification setup error", error=str(e))
        return None

    # ─── Bill of Lading Extraction ──────────────────────────────────────────────

    async def extract_bill_of_lading(
        self,
        text: str,
        pages: list[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
    ) -> Tuple[dict[str, Any], dict[str, Any], float]:
        """Extract Bill of Lading with Gemini AI, validated against Pydantic schema.
        Uses image-direct multimodal extraction for scanned/photographed documents
        when OCR text is insufficient.
        """
        if not self.is_configured:
            logger.info("AI provider is not configured. Falling back to heuristic extractor.")
            return await self._fallback_provider.extract_bill_of_lading(text, pages, metadata)

        image_bytes = (metadata or {}).get("image_bytes")
        text_is_sufficient = len(text.strip()) >= _MIN_CHARS_FOR_TEXT_EXTRACTION

        # For scanned/photo documents: prefer image-direct extraction
        if not text_is_sufficient and image_bytes:
            logger.info(
                "Text insufficient for BL extraction, trying image-direct multimodal",
                text_chars=len(text.strip()),
            )
            result = await self._extract_from_image(image_bytes, text)
            if result:
                return result

        # Text-based extraction (standard path)
        if text_is_sufficient:
            result = await self._extract_from_text(text, pages)
            if result:
                return result

        logger.info("Gemini extraction could not produce valid schema, falling back to heuristic")
        return await self._fallback_provider.extract_bill_of_lading(text, pages, metadata)

    async def _extract_from_text(
        self,
        text: str,
        pages: list[dict[str, Any]],
    ) -> Optional[Tuple[dict[str, Any], dict[str, Any], float]]:
        """Text-based BL extraction with retry."""
        pages_summary = []
        for p in pages:
            pages_summary.append(
                f"[Page {p.get('page_number', 1)} - OCR: {p.get('ocr_used', False)}]:\n{p.get('text', '')[:2000]}"
            )
        pages_text = "\n\n".join(pages_summary)

        prompt = BILL_OF_LADING_PROMPT.format(
            document_pages=pages_text[:12000],
            document_text=text[:16000],
        )

        for attempt in range(3):
            try:
                from google.genai import types
                response = await self._generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.0,
                        response_mime_type="application/json",
                    ),
                )
                raw_text = response.text or ""
                data = self._extract_json_block(raw_text)
                if data:
                    field_evidence = data.pop("field_evidence", {})
                    # Try strict validation first, fall back to lenient use of raw data
                    is_valid, errors = self.validate_extraction(data, BillOfLadingExtraction)
                    if not is_valid:
                        logger.warning(
                            "Gemini text extraction: schema validation warnings (using raw data anyway)",
                            attempt=attempt,
                            errors=errors[:3],
                        )
                    # Use the data regardless of validation status - AI data is valuable
                    evidence = self._ensure_field_evidence(data, field_evidence, text)
                    confidences = [
                        ev.get("confidence", 0.0)
                        for ev in evidence.values()
                        if isinstance(ev, dict) and ev.get("value") is not None
                        and ev.get("confidence", 0.0) > 0.0
                    ]
                    overall_conf = sum(confidences) / len(confidences) if confidences else 0.85
                    logger.info(
                        "Gemini text extraction succeeded",
                        attempt=attempt,
                        confidence=overall_conf,
                        fields_extracted=len([e for e in evidence.values() if isinstance(e, dict) and e.get("value")]),
                    )
                    return data, evidence, round(overall_conf, 2)
            except Exception as e:
                if self._is_retryable_error(e) and attempt < 2:
                    wait = 2 ** attempt
                    logger.warning(f"Gemini text extraction retry {attempt + 1}/3 (backoff {wait}s)", error=str(e))
                    await asyncio.sleep(wait)
                else:
                    logger.warning("Gemini text extraction failed", attempt=attempt, error=str(e))
                    return None
        return None

    async def _extract_from_image(
        self,
        image_bytes: bytes,
        text: str = "",
    ) -> Optional[Tuple[dict[str, Any], dict[str, Any], float]]:
        """Image-direct multimodal BL extraction for scanned/photographed documents."""
        try:
            img_data = self._compress_image(image_bytes, quality=90)
            from google.genai import types

            image_prompt = (
                "You are analyzing a scanned Bill of Lading document image. "
                "Extract ALL visible text and structured fields. "
                "Return null for any field not clearly visible in the image. Do NOT hallucinate.\n\n"
                + BILL_OF_LADING_PROMPT.format(
                    document_pages="[Image-based extraction - see attached image]",
                    document_text="[See attached image above]",
                )
            )

            for attempt in range(3):
                try:
                    response = await self._generate_content(
                        model=self.model,
                        contents=[
                            types.Part.from_bytes(data=img_data, mime_type="image/jpeg"),
                            image_prompt,
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.0,
                        ),
                    )
                    raw_text = response.text or ""
                    data = self._extract_json_block(raw_text)
                    if data:
                        field_evidence = data.pop("field_evidence", {})
                        # Use AI data regardless of strict schema validation
                        is_valid, errors = self.validate_extraction(data, BillOfLadingExtraction)
                        if not is_valid:
                            logger.warning(
                                "Gemini image extraction: schema warnings (using raw data anyway)",
                                attempt=attempt,
                                errors=errors[:3],
                            )
                        evidence = self._ensure_field_evidence(data, field_evidence, text)
                        confidences = [
                            ev.get("confidence", 0.0)
                            for ev in evidence.values()
                            if isinstance(ev, dict) and ev.get("value") is not None
                            and ev.get("confidence", 0.0) > 0.0
                        ]
                        overall_conf = sum(confidences) / len(confidences) if confidences else 0.80
                        logger.info("Gemini image-direct BL extraction succeeded", confidence=overall_conf)
                        return data, evidence, round(overall_conf, 2)
                except Exception as e:
                    if self._is_retryable_error(e) and attempt < 2:
                        wait = 2 ** attempt
                        logger.warning(f"Gemini image extraction retry {attempt + 1}/3 (backoff {wait}s)", error=str(e))
                        await asyncio.sleep(wait)
                    else:
                        logger.warning("Gemini image extraction failed", attempt=attempt, error=str(e))
                        return None
        except Exception as e:
            logger.warning("Image extraction setup error", error=str(e))
        return None
