"""
Document Vision Debug & Annotation Rendering Service.

Provides visual diagnostics:
- Draws detected OCR text boxes with confidence badges
- Outlines layout and table regions with color-coded boundaries
- Highlights identified field labels (in Amber/Gold)
- Highlights selected field values (in Emerald/Cyan)
- Draws directed arrows/connecting lines from [Label] → [Value]
- Generates high-resolution annotated JPEG/PNG or JSON metadata for developers
"""
import io
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.core.logging import get_logger
from app.services.vision.paddle_vision_service import LayoutRegion, PageVisionResult, TextBox
from app.services.vision.spatial_associator import ValueCandidate

logger = get_logger(__name__)


class AnnotationService:
    """Renders visual diagnostic overlay maps onto document page images."""

    # Color Palette (BGR for OpenCV)
    COLOR_BOX = (200, 200, 200)          # Light Gray for generic text
    COLOR_LABEL = (0, 165, 255)          # Orange/Amber for detected Labels
    COLOR_VALUE = (0, 220, 0)            # Bright Green for selected Values
    COLOR_ARROW = (255, 0, 128)          # Magenta/Pink for Label -> Value Connection
    COLOR_LAYOUT = (255, 100, 0)         # Blue for Layout Regions
    COLOR_TABLE = (180, 0, 255)          # Purple for Tables

    @classmethod
    def render_annotated_page(
        cls,
        base_image_rgb: np.ndarray,
        vision_result: PageVisionResult,
        field_candidates: Dict[str, ValueCandidate],
        include_text_boxes: bool = True,
        include_layout: bool = True,
        include_connections: bool = True,
    ) -> np.ndarray:
        """
        Renders complete debug diagnostic overlay onto the document page.
        Returns annotated RGB NumPy image.
        """
        img = base_image_rgb.copy()
        # Convert to BGR for OpenCV drawing
        canvas = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # 1. Draw Layout Regions
        if include_layout and vision_result.layout_regions:
            for region in vision_result.layout_regions:
                x1, y1, x2, y2 = [int(c) for c in region.bbox]
                # Dashed or translucent border
                cv2.rectangle(canvas, (x1, y1), (x2, y2), cls.COLOR_LAYOUT, 2)
                tag = f"[{region.region_type}]"
                cv2.putText(canvas, tag, (x1 + 4, max(15, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cls.COLOR_LAYOUT, 1)

        # 2. Draw Table Regions
        if vision_result.tables:
            for tbl in vision_result.tables:
                x1, y1, x2, y2 = [int(c) for c in tbl.bbox]
                cv2.rectangle(canvas, (x1, y1), (x2, y2), cls.COLOR_TABLE, 2)
                cv2.putText(canvas, "[TABLE]", (x1 + 4, y1 + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cls.COLOR_TABLE, 2)

        # 3. Draw Generic Text Boxes
        if include_text_boxes and vision_result.text_boxes:
            for box in vision_result.text_boxes:
                x1, y1, x2, y2 = [int(c) for c in box.bbox]
                cv2.rectangle(canvas, (x1, y1), (x2, y2), cls.COLOR_BOX, 1)

        # 4. Highlight Associated Labels, Values, and draw Connecting Arrows
        if include_connections and field_candidates:
            for field_name, cand in field_candidates.items():
                if cand.source_page != vision_result.page_number:
                    continue

                # Draw Label Box (Amber)
                lx1, ly1, lx2, ly2 = [int(c) for c in cand.label_bbox]
                cv2.rectangle(canvas, (lx1, ly1), (lx2, ly2), cls.COLOR_LABEL, 2)
                label_tag = f"LABEL: {field_name}"
                cv2.putText(canvas, label_tag, (lx1, max(14, ly1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cls.COLOR_LABEL, 1)

                # Draw Value Box (Green)
                vx1, vy1, vx2, vy2 = [int(c) for c in cand.source_bbox]
                cv2.rectangle(canvas, (vx1, vy1), (vx2, vy2), cls.COLOR_VALUE, 2)
                val_tag = f"VAL: {cand.value_raw[:20]} ({int(cand.confidence*100)}%)"
                cv2.putText(canvas, val_tag, (vx1, vy2 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cls.COLOR_VALUE, 1)

                # Draw Connection Arrow from Label center to Value center
                label_center = ((lx1 + lx2) // 2, (ly1 + ly2) // 2)
                value_center = ((vx1 + vx2) // 2, (vy1 + vy2) // 2)
                cv2.arrowedLine(
                    canvas,
                    label_center,
                    value_center,
                    cls.COLOR_ARROW,
                    2,
                    tipLength=0.15,
                )

        # Convert back to RGB
        return cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)

    @classmethod
    def get_annotated_jpeg_bytes(
        cls,
        base_image_rgb: np.ndarray,
        vision_result: PageVisionResult,
        field_candidates: Dict[str, ValueCandidate],
        quality: int = 85,
    ) -> bytes:
        """Returns the annotated image encoded as JPEG byte stream."""
        annotated_rgb = cls.render_annotated_page(base_image_rgb, vision_result, field_candidates)
        pil_img = Image.fromarray(annotated_rgb)
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
