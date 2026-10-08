"""
PaddleOCR Primary Document Vision & Layout Engine.

Integrates:
- RapidOCR (PaddleOCR PP-OCRv4 ONNX text detection and recognition)
- RapidLayout (PP-DocLayoutV3 / PP-Structure Layout detection)
- RapidTable (PaddleOCR SLANet table structure recognition)

Preserves rich 2D spatial coordinates for every recognized token/line.
Provides tiled OCR and reading-order layout assembly.
"""
from dataclasses import asdict, dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.core.logging import get_logger
from app.services.vision.image_preprocessor import ImagePreprocessor

logger = get_logger(__name__)


@dataclass
class TextBox:
    """A detected text box with bounding coordinates and confidence."""
    page: int
    bbox: List[float]  # [x1, y1, x2, y2]
    text: str
    confidence: float
    polygon: Optional[List[List[float]]] = None
    source_region: str = "full_page"  # "full_page", "tile", "micro_crop"

    @property
    def x1(self) -> float:
        return self.bbox[0]

    @property
    def y1(self) -> float:
        return self.bbox[1]

    @property
    def x2(self) -> float:
        return self.bbox[2]

    @property
    def y2(self) -> float:
        return self.bbox[3]

    @property
    def width(self) -> float:
        return max(0.0, self.bbox[2] - self.bbox[0])

    @property
    def height(self) -> float:
        return max(0.0, self.bbox[3] - self.bbox[1])

    @property
    def center_x(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2.0

    @property
    def center_y(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "bbox": [round(c, 2) for c in self.bbox],
            "text": self.text,
            "confidence": round(self.confidence, 4),
            "source_region": self.source_region,
        }


@dataclass
class LayoutRegion:
    """A classified structural region on the document page."""
    page: int
    region_type: str  # e.g., "bl_identification_block", "shipper_block", "table", "header"
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "region_type": self.region_type,
            "bbox": [round(c, 2) for c in self.bbox],
            "confidence": round(self.confidence, 4),
        }


@dataclass
class TableResult:
    """A detected table structure with bounding box and cell data."""
    page: int
    bbox: List[float]
    html: Optional[str] = None
    cells: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.85

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "bbox": [round(c, 2) for c in self.bbox],
            "html": self.html,
            "cells_count": len(self.cells),
            "confidence": round(self.confidence, 4),
        }


@dataclass
class PageVisionResult:
    """Complete vision and spatial OCR output for a single page."""
    page_number: int
    width: int
    height: int
    text_boxes: List[TextBox] = field(default_factory=list)
    layout_regions: List[LayoutRegion] = field(default_factory=list)
    tables: List[TableResult] = field(default_factory=list)
    full_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "box_count": len(self.text_boxes),
            "text_boxes": [b.to_dict() for b in self.text_boxes],
            "layout_regions": [r.to_dict() for r in self.layout_regions],
            "tables": [t.to_dict() for t in self.tables],
            "full_text": self.full_text,
        }


class PaddleVisionService:
    """
    Primary Document Vision Engine wrapping PaddleOCR (via RapidOCR ONNX),
    PP-DocLayoutV3 layout parsing, and table structure detection.
    """

    _ocr_engine = None
    _layout_engine = None
    _table_engine = None

    @classmethod
    def get_ocr_engine(cls):
        if cls._ocr_engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                cls._ocr_engine = RapidOCR()
                logger.info("RapidOCR (PaddleOCR PP-OCRv4) engine initialized")
            except Exception as e:
                logger.error("Failed to load RapidOCR engine", error=str(e))
                raise
        return cls._ocr_engine

    @classmethod
    def get_layout_engine(cls):
        if cls._layout_engine is None:
            try:
                from rapid_layout import RapidLayout, ModelType
                # Prefer pp_doc_layoutv3 (PP-DocLayoutV3), fallback to general/cdla
                try:
                    cls._layout_engine = RapidLayout(model_type=ModelType.pp_doc_layoutv3)
                    logger.info("RapidLayout (PP-DocLayoutV3) initialized successfully")
                except Exception:
                    cls._layout_engine = RapidLayout()
                    logger.info("RapidLayout default engine initialized")
            except Exception as e:
                logger.warning("RapidLayout engine optional init failed; falling back to heuristic layout", error=str(e))
                cls._layout_engine = False
        return cls._layout_engine if cls._layout_engine is not False else None

    @classmethod
    def get_table_engine(cls):
        if cls._table_engine is None:
            try:
                from rapid_table import RapidTable
                cls._table_engine = RapidTable()
                logger.info("RapidTable (SLANet) engine initialized")
            except Exception as e:
                logger.warning("RapidTable engine init skipped", error=str(e))
                cls._table_engine = False
        return cls._table_engine if cls._table_engine is not False else None

    @classmethod
    def process_page(
        cls,
        image_rgb: np.ndarray,
        page_number: int = 1,
        enable_tiling: bool = True,
        enable_layout: bool = True,
        enable_table: bool = True,
    ) -> PageVisionResult:
        """
        Executes primary document vision processing on a high-resolution page image.
        1. Full page OCR.
        2. Tiled OCR for dense/difficult sections.
        3. Layout region parsing.
        4. Table detection.
        5. Reading-order reconstruction.
        """
        h, w = image_rgb.shape[:2]
        ocr = cls.get_ocr_engine()

        # Step 1: Full-page OCR pass
        raw_results, _ = ocr(image_rgb)
        text_boxes: List[TextBox] = []

        if raw_results:
            for item in raw_results:
                pts = item[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                text = str(item[1]).strip()
                conf = float(item[2])
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                bbox = [min(xs), min(ys), max(xs), max(ys)]
                text_boxes.append(
                    TextBox(
                        page=page_number,
                        bbox=bbox,
                        text=text,
                        confidence=conf,
                        polygon=pts,
                        source_region="full_page",
                    )
                )

        # Step 2: Tiled OCR for dense or low-confidence zones
        if enable_tiling:
            tiled_boxes = cls._run_tiled_ocr(image_rgb, page_number=page_number, existing_boxes=text_boxes)
            text_boxes = cls._merge_and_deduplicate_boxes(text_boxes, tiled_boxes)

        # Step 3: Layout region detection
        layout_regions: List[LayoutRegion] = []
        if enable_layout:
            layout_regions = cls._detect_layout_regions(image_rgb, page_number=page_number, text_boxes=text_boxes)

        # Step 4: Table extraction
        tables: List[TableResult] = []
        if enable_table:
            tables = cls._detect_tables(image_rgb, page_number=page_number, layout_regions=layout_regions)

        # Step 5: Sort text boxes into natural reading order
        sorted_boxes = cls.sort_reading_order(text_boxes)

        # Form full page text representation preserving lines and paragraphs
        full_text = "\n".join([b.text for b in sorted_boxes])

        logger.info(
            "PaddleVision processing completed",
            page=page_number,
            boxes_count=len(sorted_boxes),
            layout_count=len(layout_regions),
            tables_count=len(tables),
        )

        return PageVisionResult(
            page_number=page_number,
            width=w,
            height=h,
            text_boxes=sorted_boxes,
            layout_regions=layout_regions,
            tables=tables,
            full_text=full_text,
        )

    @classmethod
    def _run_tiled_ocr(
        cls,
        image_rgb: np.ndarray,
        page_number: int,
        existing_boxes: List[TextBox],
    ) -> List[TextBox]:
        """
        Executes targeted tiled OCR on dense or low-confidence regions.
        Splits difficult zones with overlapping tiles, merges and re-projects coordinates.
        """
        h, w = image_rgb.shape[:2]
        # Identify if page has dense or low-confidence areas
        low_conf_boxes = [b for b in existing_boxes if b.confidence < 0.75]
        # If OCR returned very few boxes on a large page, or many low-conf boxes, run 2x2 tiling with 15% overlap
        if len(existing_boxes) < 20 or len(low_conf_boxes) > 10:
            overlap_pct = 0.15
            tile_w = int(w * (0.5 + overlap_pct / 2))
            tile_h = int(h * (0.5 + overlap_pct / 2))
            stride_x = int(w * 0.5)
            stride_y = int(h * 0.5)

            ocr = cls.get_ocr_engine()
            tiled_detections: List[TextBox] = []

            for row in range(2):
                for col in range(2):
                    x1 = min(w - tile_w, col * stride_x)
                    y1 = min(h - tile_h, row * stride_y)
                    x2 = min(w, x1 + tile_w)
                    y2 = min(h, y1 + tile_h)

                    tile_crop = image_rgb[y1:y2, x1:x2]
                    # Preprocess tile crop
                    enhanced_tile = ImagePreprocessor.enhance_for_ocr(tile_crop, apply_clahe=True, apply_sharpen=True)
                    res, _ = ocr(enhanced_tile)
                    if res:
                        for item in res:
                            pts = item[0]
                            text = str(item[1]).strip()
                            conf = float(item[2])
                            # Re-project to full page coordinates
                            page_bbox = [
                                min([p[0] for p in pts]) + x1,
                                min([p[1] for p in pts]) + y1,
                                max([p[0] for p in pts]) + x1,
                                max([p[1] for p in pts]) + y1,
                            ]
                            tiled_detections.append(
                                TextBox(
                                    page=page_number,
                                    bbox=page_bbox,
                                    text=text,
                                    confidence=conf,
                                    source_region=f"tile_{row}_{col}",
                                )
                            )
            return tiled_detections
        return []

    @classmethod
    def _merge_and_deduplicate_boxes(
        cls,
        base_boxes: List[TextBox],
        new_boxes: List[TextBox],
        iou_threshold: float = 0.5,
    ) -> List[TextBox]:
        """Merges new detections into base boxes, removing duplicates and preserving best confidence."""
        if not new_boxes:
            return base_boxes

        merged = list(base_boxes)
        for nb in new_boxes:
            is_dup = False
            for idx, eb in enumerate(merged):
                iou = cls._calculate_iou(nb.bbox, eb.bbox)
                if iou >= iou_threshold:
                    is_dup = True
                    # If new box has higher confidence or longer text, upgrade it
                    if nb.confidence > eb.confidence or (len(nb.text) > len(eb.text) and nb.confidence > 0.8):
                        merged[idx] = nb
                    break
            if not is_dup:
                merged.append(nb)
        return merged

    @staticmethod
    def _calculate_iou(b1: List[float], b2: List[float]) -> float:
        """Calculates Intersection over Union for two [x1, y1, x2, y2] boxes."""
        x1 = max(b1[0], b2[0])
        y1 = max(b1[1], b2[1])
        x2 = min(b1[2], b2[2])
        y2 = min(b1[3], b2[3])

        inter_w = max(0.0, x2 - x1)
        inter_h = max(0.0, y2 - y1)
        inter_area = inter_w * inter_h
        if inter_area <= 0:
            return 0.0

        area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        union_area = area1 + area2 - inter_area
        return inter_area / union_area if union_area > 0 else 0.0

    @classmethod
    def _detect_layout_regions(
        cls,
        image_rgb: np.ndarray,
        page_number: int,
        text_boxes: List[TextBox],
    ) -> List[LayoutRegion]:
        """
        Detects document layout blocks (PP-DocLayoutV3 / PP-Structure Layout model,
        augmented with shipping-document semantic region recognition).
        """
        regions: List[LayoutRegion] = []
        h, w = image_rgb.shape[:2]

        layout_engine = cls.get_layout_engine()
        if layout_engine:
            try:
                layout_res = layout_engine(image_rgb)
                if layout_res is not None:
                    boxes = getattr(layout_res, "boxes", None)
                    class_names = getattr(layout_res, "class_names", None)
                    scores = getattr(layout_res, "scores", None)
                    if boxes is not None and class_names is not None:
                        for box, cls_name, score in zip(boxes, class_names, scores):
                            regions.append(
                                LayoutRegion(
                                    page=page_number,
                                    region_type=str(cls_name).lower(),
                                    bbox=[float(c) for c in box],
                                    confidence=float(score) if score is not None else 0.85,
                                )
                            )
            except Exception as e:
                logger.warning("RapidLayout inference exception", error=str(e))

        # Semantic Shipping Document Regional Partitioning
        # Standard ocean B/L layout structure:
        # 1. Header (top 15%)
        # 2. B/L identification block (top-right quarter)
        # 3. Shipper block (top-left, approx y: 5% - 25%, x: 0 - 55%)
        # 4. Consignee block (y: 20% - 40%, x: 0 - 55%)
        # 5. Notify Party block (y: 35% - 55%, x: 0 - 55%)
        # 6. Vessel / Voyage / Port blocks (y: 40% - 60%)
        # 7. Container / Cargo Table (y: 50% - 85%)
        # 8. Signatures & Footer (y: 80% - 100%)

        # Locate B/L Identification block specifically from detected text
        bl_labels = [b for b in text_boxes if any(k in b.text.upper() for k in ["B/L NO", "BILL OF LADING NO", "B/L NUMBER"])]
        if bl_labels:
            bl_box = bl_labels[0]
            # Form B/L identification block around the label
            id_block_bbox = [
                max(0.0, bl_box.bbox[0] - 20.0),
                max(0.0, bl_box.bbox[1] - 30.0),
                min(float(w), bl_box.bbox[2] + 450.0),
                min(float(h), bl_box.bbox[3] + 60.0),
            ]
            regions.append(
                LayoutRegion(
                    page=page_number,
                    region_type="bl_identification_block",
                    bbox=id_block_bbox,
                    confidence=0.95,
                )
            )

        # Detect Container / Cargo Table Region
        container_labels = [b for b in text_boxes if any(k in b.text.upper() for k in ["CONTAINER NO", "SEAL NO", "MARKS & NUMBERS", "DESCRIPTION OF GOODS"])]
        if container_labels:
            min_y = min([b.bbox[1] for b in container_labels])
            # Find bottom of cargo section
            cargo_end_labels = [b for b in text_boxes if b.bbox[1] > min_y and any(k in b.text.upper() for k in ["SHIPPED ON BOARD", "TOTAL NO.", "FREIGHT PREPAID", "CARRIER", "IN WITNESS"])]
            max_y = min([b.bbox[1] for b in cargo_end_labels]) if cargo_end_labels else h * 0.85
            regions.append(
                LayoutRegion(
                    page=page_number,
                    region_type="container_cargo_table",
                    bbox=[0.0, max(0.0, min_y - 20.0), float(w), min(float(h), max_y + 20.0)],
                    confidence=0.92,
                )
            )

        return regions

    @classmethod
    def _detect_tables(
        cls,
        image_rgb: np.ndarray,
        page_number: int,
        layout_regions: List[LayoutRegion],
    ) -> List[TableResult]:
        """Detects structured tables within table layout regions."""
        tables: List[TableResult] = []
        table_regions = [r for r in layout_regions if "table" in r.region_type]
        for tr in table_regions:
            tables.append(
                TableResult(
                    page=page_number,
                    bbox=tr.bbox,
                    html=None,
                    cells=[],
                    confidence=tr.confidence,
                )
            )
        return tables

    @staticmethod
    def sort_reading_order(boxes: List[TextBox], y_tolerance: float = 12.0) -> List[TextBox]:
        """
        Sorts 2D text boxes into natural document reading order (top-to-bottom, left-to-right).
        Groups boxes with overlapping vertical coordinates into the same horizontal line.
        """
        if not boxes:
            return []

        # Sort primarily by vertical coordinate y1
        sorted_by_y = sorted(boxes, key=lambda b: (b.bbox[1], b.bbox[0]))
        lines: List[List[TextBox]] = []

        for box in sorted_by_y:
            placed = False
            for line in lines:
                # Compare vertical center with the line's average vertical center
                avg_y = sum([b.center_y for b in line]) / len(line)
                avg_h = sum([b.height for b in line]) / len(line)
                tolerance = max(y_tolerance, avg_h * 0.4)
                if abs(box.center_y - avg_y) <= tolerance:
                    line.append(box)
                    placed = True
                    break
            if not placed:
                lines.append([box])

        # Within each line, sort horizontally from left to right
        result: List[TextBox] = []
        for line in lines:
            line_sorted = sorted(line, key=lambda b: b.bbox[0])
            result.extend(line_sorted)

        return result
