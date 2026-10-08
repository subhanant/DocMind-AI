"""
OCR (Optical Character Recognition) Service.

Supports:
- Scanned PDF pages (rendered to image)
- PNG, JPG, JPEG, WEBP images

Architecture:
- BaseOCRProvider (Base interface)
- TesseractOCRProvider (Native Tesseract via pytesseract)
- GeminiOCRProvider (Gemini AI multimodal OCR provider)
- FallbackOCRProvider (Graceful fallback)
- OCRService (High-level orchestrator)
- DocumentOCRService (Alias for backward compatibility)
"""
import io
import os
import shutil
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

from PIL import Image

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class BaseOCRProvider(ABC):
    """Abstract base class for OCR engines."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this OCR provider can be executed in the current environment."""
        ...

    @abstractmethod
    def recognize_image(self, image: Image.Image, lang: str = "eng") -> str:
        """Perform OCR on a PIL Image and return extracted text."""
        ...


class TesseractOCRProvider(BaseOCRProvider):
    """Tesseract implementation using pytesseract."""

    def __init__(self, lang: Optional[str] = None):
        self.lang = lang or settings.OCR_LANGUAGE
        self._tesseract_cmd = self._find_tesseract_binary()

    def _find_tesseract_binary(self) -> Optional[str]:
        # Check environment variable
        env_cmd = os.environ.get("TESSERACT_CMD")
        if env_cmd and os.path.isfile(env_cmd):
            return env_cmd

        # Check PATH
        path_cmd = shutil.which("tesseract")
        if path_cmd:
            return path_cmd

        # Check standard Windows paths
        common_windows_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for p in common_windows_paths:
            if os.path.isfile(p):
                return p
        return None

    def is_available(self) -> bool:
        if not settings.OCR_ENABLED:
            return False
        return self._tesseract_cmd is not None

    def recognize_image(self, image: Image.Image, lang: str = "eng") -> str:
        if not self.is_available():
            raise RuntimeError("Tesseract OCR binary is not available.")

        import pytesseract
        if self._tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd

        # Ensure image is in RGB or L mode
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        text = pytesseract.image_to_string(image, lang=lang or self.lang)
        return text.strip()


class GeminiOCRProvider(BaseOCRProvider):
    """
    Gemini Multimodal OCR Provider.
    Uses Gemini AI model to perform optical character recognition directly on images.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.AI_MODEL
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning("Failed to initialize Gemini OCR Client", error=str(e))

    def is_available(self) -> bool:
        return self._client is not None and bool(self.api_key)

    def recognize_image(self, image: Image.Image, lang: str = "eng") -> str:
        if not self.is_available():
            raise RuntimeError("Gemini OCR is not available.")

        from google.genai import types

        buf = io.BytesIO()
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(buf, format="JPEG", quality=90)
        img_bytes = buf.getvalue()

        # Try primary model followed by fallback candidate models
        models_to_try = [self.model]
        for m_cand in ["gemini-flash-lite-latest", "gemini-3.1-flash-lite-preview", "gemini-3.5-flash", "gemini-3.8-flash"]:
            if m_cand not in models_to_try:
                models_to_try.append(m_cand)

        last_error = None
        for m in models_to_try:
            for attempt in range(2):
                try:
                    response = self._client.models.generate_content(
                        model=m,
                        contents=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                            "Perform optical character recognition (OCR) on this shipping / trade document image. "
                            "Extract and transcribe ALL visible text exactly as printed, preserving words, identifiers, codes, dates, and numbers. "
                            "Return ONLY the extracted raw text without any markdown commentary or explanation.",
                        ],
                    )
                    text = (response.text or "").strip()
                    if text:
                        logger.info("Gemini OCR succeeded", model=m, char_count=len(text))
                        return text
                except Exception as e:
                    last_error = e
                    err_msg = str(e)
                    if ("503" in err_msg or "UNAVAILABLE" in err_msg) and attempt == 0:
                        import time; time.sleep(1.5)
                        continue
                    logger.warning("Gemini OCR model failed, trying next candidate", model=m, error=err_msg[:120])
                    break

        if last_error:
            logger.warning("All Gemini OCR candidate models failed", error=str(last_error))
            raise last_error
        return ""


class FallbackOCRProvider(BaseOCRProvider):
    """
    Fallback OCR Provider.
    If native Tesseract binary and Gemini are unavailable,
    provides a non-crashing OCR layer.
    """

    def is_available(self) -> bool:
        return True

    def recognize_image(self, image: Image.Image, lang: str = "eng") -> str:
        logger.info(
            "Using fallback OCR handler",
            dimensions=f"{image.width}x{image.height}",
            mode=image.mode,
        )
        return ""


class OCRService:
    """
    High-level OCR Service that orchestrates OCR providers.
    Supports scanned PDFs, PNG, JPG, JPEG, WEBP.
    """

    def __init__(self, provider: Optional[BaseOCRProvider] = None):
        self._tesseract = TesseractOCRProvider()
        self._gemini = GeminiOCRProvider()
        self._fallback = FallbackOCRProvider()
        self._custom_provider = provider

    @property
    def active_provider_name(self) -> str:
        if self._custom_provider and self._custom_provider.is_available():
            return self._custom_provider.__class__.__name__
        if self._tesseract.is_available():
            return "tesseract"
        if self._gemini.is_available():
            return "gemini_ocr"
        return "fallback"

    def perform_ocr_on_image(self, image_data: bytes, lang: Optional[str] = None) -> Tuple[str, str]:
        """
        Run OCR on raw image bytes.
        Returns (extracted_text, provider_used).
        """
        try:
            image = Image.open(io.BytesIO(image_data))
        except Exception as e:
            logger.error("Failed to decode image for OCR", error=str(e))
            return "", "error"

        lang_code = lang or settings.OCR_LANGUAGE

        # 1. Custom provider if supplied
        if self._custom_provider and self._custom_provider.is_available():
            try:
                text = self._custom_provider.recognize_image(image, lang=lang_code)
                if text.strip():
                    return text, self._custom_provider.__class__.__name__
            except Exception as e:
                logger.warning("Custom OCR provider failed", error=str(e))

        # 2. Native Tesseract if installed and available
        if self._tesseract.is_available():
            try:
                text = self._tesseract.recognize_image(image, lang=lang_code)
                if text.strip():
                    return text, "tesseract"
            except Exception as e:
                logger.warning("Tesseract OCR execution failed", error=str(e))

        # 3. Gemini Multimodal OCR if configured
        if self._gemini.is_available():
            try:
                text = self._gemini.recognize_image(image, lang=lang_code)
                if text.strip():
                    return text, "gemini_ocr"
            except Exception as e:
                logger.warning("Gemini OCR execution failed", error=str(e))

        # 4. Fallback provider
        text = self._fallback.recognize_image(image, lang=lang_code)
        return text, "fallback"

    def perform_ocr_on_pil_image(self, image: Image.Image, lang: Optional[str] = None) -> Tuple[str, str]:
        """Run OCR on a PIL Image."""
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return self.perform_ocr_on_image(buf.getvalue(), lang=lang)


# Global singleton
_default_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    global _default_ocr_service
    if _default_ocr_service is None:
        _default_ocr_service = OCRService()
    return _default_ocr_service


# Backward-compatible wrapper for legacy tests
class DocumentOCRService:
    @classmethod
    def extract_from_bytes(cls, file_bytes: bytes, filename: str, mime_type: str = "application/octet-stream") -> Any:
        from app.services.text_extraction_service import DocumentTextExtractor
        extractor = DocumentTextExtractor()
        pages_res = extractor.extract_pages(file_bytes, filename, mime_type)
        return pages_res
