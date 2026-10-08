"""
Gemini Multimodal Visual Verification and Conflict Resolution Service.

Gemini's Role:
- Multimodal visual verification of high-resolution image crops & page pixels
- Semantic label/value association confirmation
- Resolution of OCR ambiguities
- Agreement boosting and disagreement arbitration
"""
import io
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.vision.field_validators import FieldValidators
from app.services.vision.spatial_associator import ValueCandidate

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class VisualVerificationResult:
    is_verified: bool
    final_value: Optional[str]
    confidence: float
    validation_status: str
    method: str
    reason: str


class GeminiVisualVerifier:
    """Multimodal visual verification layer using official Google GenAI SDK."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.AI_MODEL
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("GeminiVisualVerifier initialized", model=self.model)
            except Exception as e:
                logger.warning("Failed to initialize Google GenAI Client in VisualVerifier", error=str(e))

    @property
    def is_available(self) -> bool:
        return self._client is not None and bool(self.api_key)

    async def verify_field_candidate(
        self,
        candidate: ValueCandidate,
        page_image: np.ndarray,
    ) -> VisualVerificationResult:
        """
        Visually verifies a candidate value by sending the exact image crop to Gemini.
        Arbitrates agreement or disagreement using visual evidence and field validators.
        """
        # If Gemini is not configured, fall back to pure vision/validation result
        if not self.is_available:
            return VisualVerificationResult(
                is_verified=candidate.validation_status == "valid",
                final_value=candidate.value_raw,
                confidence=candidate.confidence,
                validation_status=candidate.validation_status,
                method="paddleocr_spatial_only",
                reason="Gemini API not configured; accepted based on spatial OCR & validation",
            )

        # Extract evidence crop from page image
        crop_bytes = self._extract_crop_bytes(page_image, candidate.evidence_crop_bbox)
        if not crop_bytes:
            return VisualVerificationResult(
                is_verified=True,
                final_value=candidate.value_raw,
                confidence=candidate.confidence,
                validation_status=candidate.validation_status,
                method="paddleocr_spatial",
                reason="Crop unavailable; using spatial detection",
            )

        try:
            from google.genai import types

            prompt = (
                f"You are a strict document vision verification engine for trade documents.\n"
                f"FIELD TO VERIFY: '{candidate.field_name}'\n"
                f"DETECTED LABEL: '{candidate.label_text}'\n"
                f"CANDIDATE VALUE: '{candidate.value_raw}'\n\n"
                f"INSTRUCTIONS:\n"
                f"1. Visually examine the provided high-resolution image crop.\n"
                f"2. Confirm the EXACT text positioned next to or under the label '{candidate.label_text}'.\n"
                f"3. Does the candidate value '{candidate.value_raw}' correctly match the actual value on the document?\n"
                f"4. If the label text is merely nearby boilerplate (like 'Received', 'Draft', 'Original'), "
                f"DO NOT return boilerplate. Identify the real printed identifier/value.\n"
                f"5. Return ONLY a valid JSON object:\n"
                f"{{\n"
                f'  "is_match": true/false,\n'
                f'  "verbatim_value": "<exact visible string or null>",\n'
                f'  "confidence": <0.0 to 1.0>,\n'
                f'  "reason": "<short explanation>"\n'
                f"}}"
            )

            response = self._client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=crop_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
            )

            res_text = response.text or ""
            parsed = self._parse_json_response(res_text)

            if parsed:
                is_match = bool(parsed.get("is_match", False))
                verbatim = parsed.get("verbatim_value")
                ai_conf = float(parsed.get("confidence", 0.90))

                # Case 1: Agreement (OCR and Gemini agree)
                if is_match or (verbatim and verbatim.strip() == candidate.value_raw.strip()):
                    # Boost confidence due to multimodal agreement
                    boosted_conf = min(1.0, round(max(candidate.confidence, ai_conf) * 1.05, 3))
                    logger.info("OCR and Gemini agreed on field", field=candidate.field_name, value=candidate.value_raw, conf=boosted_conf)
                    return VisualVerificationResult(
                        is_verified=True,
                        final_value=candidate.value_raw,
                        confidence=boosted_conf,
                        validation_status="valid",
                        method="paddleocr+gemini_visual_verified",
                        reason=parsed.get("reason", "Visual verification confirmed match"),
                    )

                # Case 2: Disagreement (Gemini identifies a different value in the visual crop)
                if verbatim and verbatim.strip() != candidate.value_raw.strip():
                    logger.info("OCR/Gemini conflict detected", ocr_val=candidate.value_raw, gemini_val=verbatim)
                    # Apply field-specific validation to both values
                    from app.services.vision.spatial_associator import SpatialAssociator
                    val_ocr = SpatialAssociator._validate_field_candidate(candidate.field_name, candidate.value_raw)
                    val_gemini = SpatialAssociator._validate_field_candidate(candidate.field_name, verbatim)

                    if val_gemini.is_valid and not val_ocr.is_valid:
                        # Gemini's visual reading is valid while OCR picked a label or noise
                        logger.info("Gemini visual reading preferred due to valid field structure", field=candidate.field_name, val=verbatim)
                        return VisualVerificationResult(
                            is_verified=True,
                            final_value=verbatim,
                            confidence=min(0.98, ai_conf),
                            validation_status="valid",
                            method="gemini_visual_correction",
                            reason=f"Corrected OCR error using visual inspection: {parsed.get('reason', '')}",
                        )
                    elif val_ocr.is_valid and not val_gemini.is_valid:
                        # OCR value is structurally valid while Gemini read extraneous text
                        return VisualVerificationResult(
                            is_verified=True,
                            final_value=candidate.value_raw,
                            confidence=candidate.confidence,
                            validation_status="valid",
                            method="paddleocr_validated",
                            reason="OCR candidate confirmed by field validator over AI alternative",
                        )
                    elif val_gemini.is_valid and val_ocr.is_valid:
                        # Both are valid; if Gemini corrected small typo, prefer Gemini
                        return VisualVerificationResult(
                            is_verified=True,
                            final_value=verbatim if len(verbatim) >= len(candidate.value_raw) else candidate.value_raw,
                            confidence=round((candidate.confidence + ai_conf) / 2.0, 3),
                            validation_status="valid",
                            method="multimodal_consensus",
                            reason="Consensus between OCR and visual inspection",
                        )

            # If still uncertain / invalid:
            if candidate.validation_status == "valid":
                return VisualVerificationResult(
                    is_verified=True,
                    final_value=candidate.value_raw,
                    confidence=candidate.confidence,
                    validation_status=candidate.validation_status,
                    method="paddleocr_spatial",
                    reason="Retained validated spatial candidate",
                )

        except Exception as e:
            logger.warning("Gemini visual verification call failed", error=str(e))

        # Fallback to candidate if valid
        return VisualVerificationResult(
            is_verified=candidate.validation_status == "valid",
            final_value=candidate.value_raw if candidate.validation_status == "valid" else None,
            confidence=candidate.confidence if candidate.validation_status == "valid" else 0.0,
            validation_status=candidate.validation_status,
            method="paddleocr_fallback",
            reason="Verification fallback",
        )

    @staticmethod
    def _extract_crop_bytes(image: np.ndarray, bbox: List[float], quality: int = 90) -> Optional[bytes]:
        """Crops region from image and encodes as JPEG bytes."""
        try:
            h, w = image.shape[:2]
            x1, y1, x2, y2 = [int(c) for c in bbox]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 <= x1 or y2 <= y1:
                return None

            crop = image[y1:y2, x1:x2]
            pil_crop = Image.fromarray(crop)
            buf = io.BytesIO()
            pil_crop.save(buf, format="JPEG", quality=quality)
            return buf.getvalue()
        except Exception:
            return None

    @staticmethod
    def _parse_json_response(text: str) -> Optional[Dict[str, Any]]:
        """Extracts JSON object from AI model text response."""
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

        m = re.search(r"(\{.*\})", clean, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        return None
