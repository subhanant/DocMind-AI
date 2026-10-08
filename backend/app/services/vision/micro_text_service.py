"""
Micro-Text & Difficult-Region Recovery Pipeline.

Architecture:
FULL PAGE OCR
    ↓
LOW-CONFIDENCE / DENSE-REGION DETECTION
    ↓
REGION CROPPING
    ↓
UPSCALE (2x - 3x Lanczos)
    ↓
IMAGE PREPROCESSING (Contrast enhancement, denoising, sharpening)
    ↓
TARGETED OCR
    ↓
RE-PROJECTION TO PAGE COORDINATES & DE-DUPLICATION
"""
from typing import List, Optional, Tuple

import cv2
import numpy as np

from app.core.logging import get_logger
from app.services.vision.image_preprocessor import ImagePreprocessor
from app.services.vision.paddle_vision_service import TextBox

logger = get_logger(__name__)


class MicroTextService:
    """Specialized recovery pipeline for small print, stamps, low-contrast text, and rider tables."""

    @classmethod
    def recover_micro_text(
        cls,
        image_rgb: np.ndarray,
        page_number: int,
        initial_boxes: List[TextBox],
        ocr_engine=None,
    ) -> List[TextBox]:
        """
        Scans for low-confidence text boxes and difficult regions.
        Crops, upscales, enhances, and performs targeted OCR.
        """
        if ocr_engine is None:
            from app.services.vision.paddle_vision_service import PaddleVisionService
            ocr_engine = PaddleVisionService.get_ocr_engine()

        h, w = image_rgb.shape[:2]
        recovered_boxes: List[TextBox] = []

        # Find low-confidence text detections or regions with small box heights (< 18px at 300 DPI)
        difficult_boxes = [b for b in initial_boxes if b.confidence < 0.70 or b.height < 20.0]

        # Group nearby difficult boxes into clusters to avoid thousands of individual micro-crops
        clusters = cls._cluster_difficult_regions(difficult_boxes, w=w, h=h)

        logger.info(
            "Micro-text scan started",
            page=page_number,
            difficult_candidates=len(difficult_boxes),
            clusters_count=len(clusters),
        )

        for cluster_bbox in clusters:
            x1, y1, x2, y2 = [int(c) for c in cluster_bbox]
            crop_w = x2 - x1
            crop_h = y2 - y1

            # Skip trivial or empty crops
            if crop_w < 10 or crop_h < 10 or crop_w > w * 0.8:
                continue

            crop = image_rgb[y1:y2, x1:x2]
            # Verify if crop contains sufficient visual variance (avoid blank paper)
            gray_crop = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
            std_dev = np.std(gray_crop)
            if std_dev < 8.0:
                # Flat paper / no visual features
                continue

            # Upscale 2.0x and apply controlled preprocessing
            enhanced_crop = ImagePreprocessor.preprocess_micro_crop(crop, scale_factor=2.0)

            # Run targeted OCR on enhanced crop
            results, _ = ocr_engine(enhanced_crop)
            if results:
                scale_inv = 1.0 / 2.0
                for item in results:
                    pts = item[0]
                    text = str(item[1]).strip()
                    conf = float(item[2])

                    # Minimum confidence threshold for micro-text recovery
                    if conf < 0.65 or len(text) < 2:
                        continue

                    # Re-project from upscaled crop coordinates back to full-page coordinates
                    orig_xs = [p[0] * scale_inv + x1 for p in pts]
                    orig_ys = [p[1] * scale_inv + y1 for p in pts]
                    page_bbox = [min(orig_xs), min(orig_ys), max(orig_xs), max(orig_ys)]

                    recovered_boxes.append(
                        TextBox(
                            page=page_number,
                            bbox=page_bbox,
                            text=text,
                            confidence=conf,
                            polygon=[[x * scale_inv + x1, y * scale_inv + y1] for x, y in pts],
                            source_region="micro_crop",
                        )
                    )

        logger.info("Micro-text recovery completed", page=page_number, recovered=len(recovered_boxes))
        return recovered_boxes

    @classmethod
    def _cluster_difficult_regions(
        cls,
        difficult_boxes: List[TextBox],
        w: int,
        h: int,
        padding: int = 15,
    ) -> List[List[float]]:
        """Groups nearby difficult text boxes into bounding clusters with padding."""
        if not difficult_boxes:
            return []

        clusters: List[List[float]] = []
        for box in difficult_boxes:
            bx1 = max(0, box.bbox[0] - padding)
            by1 = max(0, box.bbox[1] - padding)
            bx2 = min(w, box.bbox[2] + padding)
            by2 = min(h, box.bbox[3] + padding)

            merged = False
            for i, cl in enumerate(clusters):
                # Check overlap or proximity
                if not (bx2 < cl[0] or bx1 > cl[2] or by2 < cl[1] or by1 > cl[3]):
                    # Expand cluster
                    clusters[i] = [
                        min(cl[0], bx1),
                        min(cl[1], by1),
                        max(cl[2], bx2),
                        max(cl[3], by2),
                    ]
                    merged = True
                    break
            if not merged:
                clusters.append([bx1, by1, bx2, by2])

        return clusters
