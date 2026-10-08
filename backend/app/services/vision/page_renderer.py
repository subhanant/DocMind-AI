"""
High-Resolution Document Page Rendering Service.

Requirements satisfied:
- Detects total page count for PDFs and images.
- Processes EVERY page.
- Renders PDF pages at high resolution (default: 300 DPI; up to 400+ DPI for difficult regions).
- Retains original aspect ratio without downscaling before detection.
- Produces normalized image representations (PIL Image and NumPy arrays).
- Never modifies the original uploaded file.
"""
import io
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

import numpy as np
from PIL import Image
import pymupdf

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RenderedPage:
    page_number: int  # 1-indexed
    total_pages: int
    image: Image.Image  # PIL RGB Image
    numpy_image: np.ndarray  # HxWx3 uint8 RGB array
    width: int
    height: int
    dpi: int
    source_format: str  # "pdf", "image/png", etc.


class PageRenderer:
    """High-resolution rendering engine for PDFs and images."""

    DEFAULT_DPI: int = 300
    HIGH_RES_DPI: int = 400

    @classmethod
    def render_document(
        cls,
        file_bytes: bytes,
        mime_type: str,
        filename: str = "",
        dpi: int = DEFAULT_DPI,
    ) -> List[RenderedPage]:
        """
        Renders all pages of a document at high resolution.
        Returns a list of RenderedPage objects (one per page).
        """
        is_pdf = (
            "pdf" in mime_type.lower()
            or filename.lower().endswith(".pdf")
            or file_bytes[:4] == b"%PDF"
        )

        if is_pdf:
            return cls._render_pdf(file_bytes, dpi=dpi)
        else:
            return cls._render_image(file_bytes, mime_type=mime_type)

    @classmethod
    def _render_pdf(cls, file_bytes: bytes, dpi: int = DEFAULT_DPI) -> List[RenderedPage]:
        """Render all pages of a PDF document at high DPI (e.g., 300 DPI)."""
        rendered_pages: List[RenderedPage] = []
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        total_pages = len(doc)
        logger.info("Rendering PDF pages", total_pages=total_pages, dpi=dpi)

        try:
            for page_idx in range(total_pages):
                page = doc[page_idx]
                pix = page.get_pixmap(dpi=dpi, alpha=False)
                # Convert samples buffer to NumPy array (H, W, 3)
                np_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
                if pix.n == 4:
                    np_img = np_img[:, :, :3]
                elif pix.n == 1:
                    np_img = np.repeat(np_img[:, :, np.newaxis], 3, axis=2)

                pil_img = Image.fromarray(np_img, mode="RGB")

                rendered_pages.append(
                    RenderedPage(
                        page_number=page_idx + 1,
                        total_pages=total_pages,
                        image=pil_img,
                        numpy_image=np_img,
                        width=pix.width,
                        height=pix.height,
                        dpi=dpi,
                        source_format="pdf",
                    )
                )
        finally:
            doc.close()

        return rendered_pages

    @classmethod
    def _render_image(cls, file_bytes: bytes, mime_type: str = "image/jpeg") -> List[RenderedPage]:
        """Render single-page image document (PNG, JPEG, TIFF, WEBP)."""
        pil_img = Image.open(io.BytesIO(file_bytes))
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        np_img = np.array(pil_img, dtype=np.uint8)
        w, h = pil_img.size

        return [
            RenderedPage(
                page_number=1,
                total_pages=1,
                image=pil_img,
                numpy_image=np_img,
                width=w,
                height=h,
                dpi=cls.DEFAULT_DPI,
                source_format=mime_type,
            )
        ]

    @classmethod
    def render_page_at_high_res(
        cls,
        file_bytes: bytes,
        page_number: int,
        dpi: int = HIGH_RES_DPI,
    ) -> Optional[RenderedPage]:
        """Render a specific page at higher DPI for difficult/micro-text extraction."""
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        try:
            if page_number < 1 or page_number > len(doc):
                return None
            page = doc[page_number - 1]
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            np_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
            if pix.n == 4:
                np_img = np_img[:, :, :3]
            elif pix.n == 1:
                np_img = np.repeat(np_img[:, :, np.newaxis], 3, axis=2)

            pil_img = Image.fromarray(np_img, mode="RGB")
            return RenderedPage(
                page_number=page_number,
                total_pages=len(doc),
                image=pil_img,
                numpy_image=np_img,
                width=pix.width,
                height=pix.height,
                dpi=dpi,
                source_format="pdf",
            )
        finally:
            doc.close()
