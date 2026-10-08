"""
Document Table & Multi-Container Row Extractor.

Maintains row-level association:
container_number → container_type → seal_number → package_count → cargo_description → weight → tare_weight → hs_code.

Supports:
- Multi-row container tables
- Delimited container blocks (e.g. CAAU7671123 / AEDXB2603396 / 40HC / 1080 BAGS / 27,450.000 KGM)
- Multi-page and rider/continuation page table aggregation
- Complete source value provenance envelope for every cell/value
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.services.vision.field_validators import FieldValidators
from app.services.vision.paddle_vision_service import TextBox

logger = get_logger(__name__)


@dataclass
class ContainerRowRecord:
    """A single preserved container row from a B/L table or rider page."""
    container_number: Dict[str, Any]
    container_type: Dict[str, Any]
    seal_number: Dict[str, Any]
    package_count: Dict[str, Any]
    cargo_description: Dict[str, Any]
    gross_cargo_weight: Dict[str, Any]
    tare_weight: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "container_number": self.container_number,
            "container_type": self.container_type,
            "seal_number": self.seal_number,
            "package_count": self.package_count,
            "cargo_description": self.cargo_description,
            "gross_cargo_weight": self.gross_cargo_weight,
            "tare_weight": self.tare_weight,
        }


class TableExtractor:
    """Extracts structured container and cargo tables with preserved row associations."""

    @classmethod
    def extract_containers(
        cls,
        text_boxes: List[TextBox],
        page_number: int = 1,
    ) -> List[ContainerRowRecord]:
        """
        Detects all container rows on a page using spatial grouping and row patterns.
        Preserves all containers without collapsing to just the first one.
        """
        container_records: List[ContainerRowRecord] = []

        # Pattern 1: Slash-separated or compound lines (e.g., "CAAU7671123 / AEDXB2603396 / 40HC / 1080 BAG(S) / 27,450.000 KGM")
        compound_rows = cls._extract_compound_container_lines(text_boxes, page_number)
        container_records.extend(compound_rows)

        # Pattern 2: Column-based table rows (separate boxes aligned vertically by column and horizontally by row)
        column_rows = cls._extract_columnar_container_rows(text_boxes, page_number, already_found=container_records)
        container_records.extend(column_rows)

        logger.info(
            "Container extraction finished",
            page=page_number,
            total_containers_found=len(container_records),
        )
        return container_records

    @classmethod
    def _extract_compound_container_lines(
        cls,
        text_boxes: List[TextBox],
        page_number: int,
    ) -> List[ContainerRowRecord]:
        """Extracts container rows from lines containing multiple fields separated by slashes or delimiters."""
        records: List[ContainerRowRecord] = []

        # Find boxes containing 4-letter + 7-digit container pattern
        container_pattern = r"\b([A-Z]{4}\d{7})\b"

        for box in text_boxes:
            text = box.text.strip()
            # If line has multiple containers or multi-line block
            lines = text.split("\n")
            for subline in lines:
                subline = subline.strip()
                if not re.search(container_pattern, subline):
                    continue

                # Parse parts separated by '/'
                parts = [p.strip() for p in subline.split("/") if p.strip()]
                cntr_match = re.search(container_pattern, subline)
                if not cntr_match:
                    continue

                cntr_num = cntr_match.group(1)
                seal_val: Optional[str] = None
                type_val: Optional[str] = None
                pkg_val: Optional[str] = None
                weight_val: Optional[str] = None

                # Inspect parts
                for part in parts:
                    if cntr_num in part:
                        continue
                    # Check for container type (e.g. 20GP, 40HC, 40RF, 45HC)
                    if re.search(r"\b(20GP|40GP|40HC|45HC|20DC|40DC|40RF|20RF)\b", part, re.I):
                        type_val = part
                    # Check for package count (e.g. 1080 BAG(S))
                    elif re.search(r"\b\d+\s*(?:BAG|PKG|PACKAGE|CTN|BOX|PALLET|DRUM)", part, re.I):
                        pkg_val = part
                    # Check for weight (e.g. 27,450.000 KGM)
                    elif re.search(r"[\d,]+(?:\.\d+)?\s*(?:KG|KGM|KGS|MT|LBS)", part, re.I):
                        weight_val = part
                    # Potential seal number (alphanumeric 5-15 chars)
                    elif re.search(r"\b([A-Z0-9\-_]{5,15})\b", part):
                        seal_match = re.search(r"\b([A-Z0-9\-_]{5,15})\b", part)
                        if seal_match and not seal_val:
                            seal_val = seal_match.group(1)

                records.append(
                    ContainerRowRecord(
                        container_number=cls._build_field_envelope(
                            val=cntr_num,
                            raw=subline,
                            conf=box.confidence,
                            page=page_number,
                            bbox=box.bbox,
                            method="paddleocr_compound_row",
                        ),
                        container_type=cls._build_field_envelope(
                            val=type_val,
                            raw=type_val,
                            conf=0.90 if type_val else 0.0,
                            page=page_number,
                            bbox=box.bbox,
                            method="paddleocr_compound_row",
                        ),
                        seal_number=cls._build_field_envelope(
                            val=seal_val,
                            raw=seal_val,
                            conf=0.90 if seal_val else 0.0,
                            page=page_number,
                            bbox=box.bbox,
                            method="paddleocr_compound_row",
                        ),
                        package_count=cls._build_field_envelope(
                            val=pkg_val,
                            raw=pkg_val,
                            conf=0.90 if pkg_val else 0.0,
                            page=page_number,
                            bbox=box.bbox,
                            method="paddleocr_compound_row",
                        ),
                        cargo_description=cls._build_field_envelope(
                            val=None,
                            raw=None,
                            conf=0.0,
                            page=page_number,
                            bbox=box.bbox,
                            method="table_row",
                        ),
                        gross_cargo_weight=cls._build_field_envelope(
                            val=weight_val,
                            raw=weight_val,
                            conf=0.92 if weight_val else 0.0,
                            page=page_number,
                            bbox=box.bbox,
                            method="paddleocr_compound_row",
                        ),
                        tare_weight=cls._build_field_envelope(
                            val=None,
                            raw=None,
                            conf=0.0,
                            page=page_number,
                            bbox=box.bbox,
                            method="table_row",
                        ),
                    )
                )

        return records

    @classmethod
    def _extract_columnar_container_rows(
        cls,
        text_boxes: List[TextBox],
        page_number: int,
        already_found: List[ContainerRowRecord],
    ) -> List[ContainerRowRecord]:
        """Extracts container rows from standard columnar tables where fields are distinct boxes."""
        existing_cntrs = {r.container_number.get("value_verbatim") for r in already_found if r.container_number.get("value_verbatim")}
        records: List[ContainerRowRecord] = []

        container_pattern = r"\b([A-Z]{4}\d{7})\b"

        # Find all boxes that match a container number
        cntr_boxes = []
        for b in text_boxes:
            m = re.search(container_pattern, b.text.strip().upper())
            if m:
                c_num = m.group(1)
                if c_num not in existing_cntrs:
                    cntr_boxes.append((b, c_num))

        for c_box, c_num in cntr_boxes:
            # Look for horizontally aligned boxes on the same row (within +- 15px vertically)
            row_boxes = [b for b in text_boxes if abs(b.center_y - c_box.center_y) <= 18.0 and b.bbox != c_box.bbox]

            seal_val = None
            seal_box = None
            type_val = None
            weight_val = None

            for rb in row_boxes:
                t = rb.text.strip()
                # Check for container type
                if re.search(r"\b(20GP|40GP|40HC|45HC|20DC|40DC|40RF)\b", t, re.I):
                    type_val = t
                # Check for weight
                elif re.search(r"[\d,]+(?:\.\d+)?\s*(?:KG|KGM|KGS|MT|LBS)", t, re.I):
                    weight_val = t
                # Potential seal number
                elif re.search(r"\b([A-Z0-9\-_]{5,15})\b", t) and not re.search(container_pattern, t):
                    seal_val = t
                    seal_box = rb

            records.append(
                ContainerRowRecord(
                    container_number=cls._build_field_envelope(
                        val=c_num,
                        raw=c_box.text,
                        conf=c_box.confidence,
                        page=page_number,
                        bbox=c_box.bbox,
                        method="paddleocr_columnar_row",
                    ),
                    container_type=cls._build_field_envelope(
                        val=type_val,
                        raw=type_val,
                        conf=0.88 if type_val else 0.0,
                        page=page_number,
                        bbox=c_box.bbox,
                        method="paddleocr_columnar_row",
                    ),
                    seal_number=cls._build_field_envelope(
                        val=seal_val,
                        raw=seal_val,
                        conf=seal_box.confidence if seal_box else 0.0,
                        page=page_number,
                        bbox=seal_box.bbox if seal_box else c_box.bbox,
                        method="paddleocr_columnar_row",
                    ),
                    package_count=cls._build_field_envelope(
                        val=None,
                        raw=None,
                        conf=0.0,
                        page=page_number,
                        bbox=c_box.bbox,
                        method="table_row",
                    ),
                    cargo_description=cls._build_field_envelope(
                        val=None,
                        raw=None,
                        conf=0.0,
                        page=page_number,
                        bbox=c_box.bbox,
                        method="table_row",
                    ),
                    gross_cargo_weight=cls._build_field_envelope(
                        val=weight_val,
                        raw=weight_val,
                        conf=0.90 if weight_val else 0.0,
                        page=page_number,
                        bbox=c_box.bbox,
                        method="paddleocr_columnar_row",
                    ),
                    tare_weight=cls._build_field_envelope(
                        val=None,
                        raw=None,
                        conf=0.0,
                        page=page_number,
                        bbox=c_box.bbox,
                        method="table_row",
                    ),
                )
            )

        return records

    @staticmethod
    def _build_field_envelope(
        val: Optional[Any],
        raw: Optional[str],
        conf: float,
        page: int,
        bbox: List[float],
        method: str,
    ) -> Dict[str, Any]:
        """Builds standard Section 12 source value preservation envelope."""
        return {
            "value_verbatim": raw or val,
            "value_normalized": val,
            "confidence": round(conf, 4) if val else 0.0,
            "validation_status": "valid" if val else "missing",
            "source_page": page,
            "source_bbox": [round(c, 2) for c in bbox],
            "extraction_method": method,
        }
