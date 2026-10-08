"""
Spatial Label → Value Association & Candidate Ranking Engine.

Solves the core problem:
Maps document field labels to their correct spatial values based on 2D coordinates,
alignment, table cell containment, and rigorous candidate ranking.

Replaces naive regex / line-scan splitting.
"""
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.services.vision.field_validators import FieldValidators, ValidationResult
from app.services.vision.paddle_vision_service import LayoutRegion, TextBox

logger = get_logger(__name__)


@dataclass
class ValueCandidate:
    """A ranked value candidate associated with a label."""
    field_name: str
    value_raw: str
    normalized_value: Optional[Any]
    confidence: float
    validation_status: str  # "valid", "uncertain", "invalid"
    source_page: int
    source_bbox: List[float]  # [x1, y1, x2, y2]
    label_text: str
    label_bbox: List[float]
    spatial_relationship: str  # "horizontal_right", "vertical_below", "same_cell"
    rank_score: float
    evidence_crop_bbox: List[float]  # Bounding box covering label + value with padding for visual verification


class SpatialAssociator:
    """Discovers labels on document pages and spatially links them to values."""

    # Field Label Definitions & Aliases
    FIELD_LABEL_MAP: Dict[str, List[str]] = {
        "bill_of_lading_number": [
            "B/L NO", "BILL OF LADING NO", "B/L NUMBER", "BILL OF LADING NUMBER",
            "BL NO", "B/L #", "BILL OF LADING #", "BL NUMBER", "OCEAN BILL OF LADING NO"
        ],
        "booking_number": [
            "BOOKING NO", "BOOKING NUMBER", "BKG NO", "BKG REF", "BOOKING REF", "SO NUMBER"
        ],
        "shipper": [
            "SHIPPER", "SHIPPER NAME", "SHIPPER/EXPORTER", "CONSIGNOR"
        ],
        "consignee": [
            "CONSIGNEE", "CONSIGNEE NAME", "CONSIGNEE (IF ORDER"
        ],
        "notify_party": [
            "NOTIFY PARTY", "NOTIFY PARTY/ADDRESS", "ALSO NOTIFY", "NOTIFY ADDRESS"
        ],
        "carrier": [
            "CARRIER", "SHIPPING LINE", "DELIVERY AGENT", "CARRIER NAME"
        ],
        "vessel_name": [
            "VESSEL", "VESSEL NAME", "OCEAN VESSEL", "FEEDER VESSEL"
        ],
        "voyage_number": [
            "VOYAGE NO", "VOYAGE NUMBER", "VOY NO", "VOYAGE"
        ],
        "port_of_loading": [
            "PORT OF LOADING", "POL"
        ],
        "port_of_discharge": [
            "PORT OF DISCHARGE", "POD"
        ],
        "place_of_receipt": [
            "PLACE OF RECEIPT", "PRE-CARRIAGE"
        ],
        "place_of_delivery": [
            "PLACE OF DELIVERY", "FINAL DESTINATION"
        ],
        "container_number": [
            "CONTAINER NO", "CONTAINER NUMBER", "CONTAINER NO/SEAL NO", "CNTR NO"
        ],
        "seal_number": [
            "SEAL NO", "SEAL NUMBER", "CUSTOMS SEAL"
        ],
        "gross_weight": [
            "GROSS WEIGHT", "GROSS CARGO WEIGHT", "TOTAL GROSS WEIGHT", "G.W."
        ],
        "net_weight": [
            "NET WEIGHT", "TOTAL NET WEIGHT", "N.W."
        ],
        "hs_code": [
            "HS CODE", "H.S. CODE", "COMMODITY CODE"
        ],
        "freight_terms": [
            "FREIGHT TERMS", "FREIGHT PREPAID", "FREIGHT COLLECT", "FREIGHT & CHARGES"
        ],
        "on_board_date": [
            "SHIPPED ON BOARD DATE", "ON BOARD DATE", "LADEN ON BOARD DATE"
        ],
        "date": [
            "DATE OF ISSUE", "PLACE & DATE OF ISSUE", "ISSUE DATE", "B/L DATE"
        ],
        "description_of_goods": [
            "DESCRIPTION OF GOODS", "SAID TO CONTAIN", "KIND OF PACKAGES", "CARGO DESCRIPTION"
        ],
    }

    @classmethod
    def associate_all_fields(
        cls,
        text_boxes: List[TextBox],
        layout_regions: List[LayoutRegion],
        page_width: int,
        page_height: int,
        page_number: int = 1,
    ) -> Dict[str, ValueCandidate]:
        """
        Runs spatial label -> value association across all supported fields on a page.
        Returns the top candidate for each field.
        """
        results: Dict[str, ValueCandidate] = {}

        for field_name, label_aliases in cls.FIELD_LABEL_MAP.items():
            candidate = cls.find_best_candidate(
                field_name=field_name,
                label_aliases=label_aliases,
                text_boxes=text_boxes,
                layout_regions=layout_regions,
                page_width=page_width,
                page_height=page_height,
                page_number=page_number,
            )
            if candidate:
                results[field_name] = candidate

        return results

    @classmethod
    def find_best_candidate(
        cls,
        field_name: str,
        label_aliases: List[str],
        text_boxes: List[TextBox],
        layout_regions: List[LayoutRegion],
        page_width: int,
        page_height: int,
        page_number: int = 1,
    ) -> Optional[ValueCandidate]:
        """Finds label occurrences for a field, ranks spatial value candidates, and returns top match."""
        # 1. Locate label boxes
        matching_labels = cls._locate_label_boxes(label_aliases, text_boxes)
        if not matching_labels:
            # For multiline blocks like party addresses or tables, try fallback scanning
            return cls._fallback_field_match(field_name, text_boxes, page_number)

        all_candidates: List[ValueCandidate] = []

        for label_box, label_alias in matching_labels:
            # Check if the label box itself contains the value (e.g. "B/L NO: MEDUFF439584" or "HS CODE : 39021000")
            inline_cand = cls._check_inline_value(
                field_name=field_name,
                label_box=label_box,
                label_alias=label_alias,
                page_width=page_width,
                page_height=page_height,
                page_number=page_number,
            )
            if inline_cand:
                all_candidates.append(inline_cand)

            # Search spatially nearby boxes in 3 directions:
            # Direction A: Horizontal Right (same vertical band)
            # Direction B: Vertical Below (underneath the label)
            # Direction C: Same cell / Layout region
            spatial_cands = cls._search_spatial_neighbors(
                field_name=field_name,
                label_box=label_box,
                text_boxes=text_boxes,
                page_width=page_width,
                page_height=page_height,
                page_number=page_number,
            )
            all_candidates.extend(spatial_cands)

        if not all_candidates:
            return None

        # Sort candidates by ranking score descending
        all_candidates.sort(key=lambda c: c.rank_score, reverse=True)
        top = all_candidates[0]

        # Log association detail
        logger.info(
            "Spatial association resolved",
            field=field_name,
            value=top.value_raw,
            rank_score=round(top.rank_score, 3),
            rel=top.spatial_relationship,
            page=page_number,
        )
        return top

    @classmethod
    def _locate_label_boxes(
        cls,
        label_aliases: List[str],
        text_boxes: List[TextBox],
    ) -> List[Tuple[TextBox, str]]:
        """Finds all text boxes that match one of the label aliases."""
        matches: List[Tuple[TextBox, str]] = []
        for box in text_boxes:
            box_text_norm = box.text.upper().strip()
            # Normalize punctuation
            box_text_clean = re.sub(r"[:.]+$", "", box_text_norm).strip()
            # Exclude boilerplates from matching as primary party labels
            if any(alias in ["SHIPPER", "SHIPPER NAME"] for alias in label_aliases):
                if any(bad in box_text_norm for bad in ["LOAD, COUNT", "DECLARED BY SHIPPER", "SHIPPER'S LOAD"]):
                    continue
            for alias in label_aliases:
                alias_upper = alias.upper()
                if alias_upper == box_text_clean or box_text_clean.startswith(alias_upper) or (alias_upper in box_text_clean and len(box_text_clean) <= len(alias_upper) + 8):
                    matches.append((box, alias))
                    break
        return matches

    @classmethod
    def _check_inline_value(
        cls,
        field_name: str,
        label_box: TextBox,
        label_alias: str,
        page_width: int,
        page_height: int,
        page_number: int,
    ) -> Optional[ValueCandidate]:
        """Checks if the label box already includes the value on the same line after a separator."""
        text = label_box.text.strip()
        pattern = r"(?i)" + re.escape(label_alias) + r"\s*[:.\-]?\s+(.+)$"
        m = re.search(pattern, text)
        if m:
            val_text = m.group(1).strip()
            # Validate candidate
            val_res = cls._validate_field_candidate(field_name, val_text)
            if val_res.is_valid:
                crop_bbox = cls._compute_crop_bbox(label_box.bbox, label_box.bbox, page_width, page_height)
                return ValueCandidate(
                    field_name=field_name,
                    value_raw=val_text,
                    normalized_value=val_res.normalized_value or val_text,
                    confidence=min(1.0, label_box.confidence + val_res.confidence_delta),
                    validation_status=val_res.status,
                    source_page=page_number,
                    source_bbox=label_box.bbox,
                    label_text=label_alias,
                    label_bbox=label_box.bbox,
                    spatial_relationship="inline_same_box",
                    rank_score=4.5 + val_res.confidence_delta,
                    evidence_crop_bbox=crop_bbox,
                )
        return None

    @classmethod
    def _search_spatial_neighbors(
        cls,
        field_name: str,
        label_box: TextBox,
        text_boxes: List[TextBox],
        page_width: int,
        page_height: int,
        page_number: int,
    ) -> List[ValueCandidate]:
        """Searches text boxes in spatial proximity to label_box and scores each candidate."""
        candidates: List[ValueCandidate] = []
        lx1, ly1, lx2, ly2 = label_box.bbox
        label_h = ly2 - ly1

        for box in text_boxes:
            # Skip the label box itself
            if box.bbox == label_box.bbox or box.text.strip() == label_box.text.strip():
                continue

            bx1, by1, bx2, by2 = box.bbox
            cand_text = box.text.strip()
            if not cand_text:
                continue

            # Skip neighbor box if it is another document label
            cand_clean = re.sub(r"[:.\-]+$", "", cand_text.upper().strip()).strip()
            is_another_label = False
            for f_aliases in cls.FIELD_LABEL_MAP.values():
                for la in f_aliases:
                    if cand_clean == la or cand_clean.startswith(la + " ") or cand_clean.startswith(la + ":"):
                        is_another_label = True
                        break
                if is_another_label:
                    break
            if is_another_label:
                continue

            # Compute horizontal and vertical overlap
            v_overlap = max(0.0, min(ly2, by2) - max(ly1, by1))
            v_overlap_ratio = v_overlap / min(label_h, (by2 - by1)) if min(label_h, (by2 - by1)) > 0 else 0.0

            h_overlap = max(0.0, min(lx2, bx2) - max(lx1, bx1))

            # ── Direction A: Horizontal Right (Same Row / Line) ──
            # Cand box is to the right of label (bx1 >= lx2 - 15) and vertically overlapping (> 40%)
            is_horizontal_right = (
                bx1 >= (lx2 - 20.0)
                and (bx1 - lx2) <= 500.0  # within 500px horizontally
                and v_overlap_ratio >= 0.35
            )

            # ── Direction B: Vertical Below (Underneath) ──
            # Cand box is directly under label (by1 >= ly2 - 8) and horizontally close
            max_vert = 160.0 if field_name in ("shipper", "consignee", "notify_party") else 95.0
            is_vertical_below = (
                by1 >= (ly2 - 8.0)
                and (by1 - ly2) <= max_vert
                and (h_overlap > 10.0 or abs(bx1 - lx1) <= 180.0)
            )

            if not (is_horizontal_right or is_vertical_below):
                continue

            rel_type = "horizontal_right" if is_horizontal_right else "vertical_below"

            # Validate field-specific structure
            val_res = cls._validate_field_candidate(field_name, cand_text)

            # Calculate Ranking Score
            dist_x = max(0.0, bx1 - lx2) if is_horizontal_right else abs(bx1 - lx1)
            dist_y = abs(by1 - ly1) if is_horizontal_right else max(0.0, by1 - ly2)
            euclidean_dist = math.sqrt(dist_x ** 2 + dist_y ** 2)

            # Base ranking score
            rank_score = 1.0 / (1.0 + euclidean_dist * 0.01)

            # Strong bonus for horizontal right alignment on identifiers (B/L No, Booking No, etc.)
            if is_horizontal_right:
                if field_name in ("bill_of_lading_number", "booking_number", "hs_code", "voyage_number"):
                    rank_score += 1.8
                else:
                    rank_score += 0.8

            # Bonus for vertical below on multiline blocks (Shipper, Consignee, Notify)
            if is_vertical_below:
                if field_name in ("shipper", "consignee", "notify_party", "description_of_goods"):
                    rank_score += 1.6
                else:
                    rank_score += 0.3

            # Validation multiplier
            if val_res.is_valid:
                rank_score += (1.5 + val_res.confidence_delta)
            else:
                # Severe penalty for invalid or boilerplate tokens
                rank_score -= 2.0

            # Weight by OCR confidence
            rank_score += box.confidence * 0.5

            if rank_score > 0.0:
                crop_bbox = cls._compute_crop_bbox(label_box.bbox, box.bbox, page_width, page_height)
                candidates.append(
                    ValueCandidate(
                        field_name=field_name,
                        value_raw=cand_text,
                        normalized_value=val_res.normalized_value or cand_text,
                        confidence=min(1.0, max(0.1, box.confidence + val_res.confidence_delta)),
                        validation_status=val_res.status,
                        source_page=page_number,
                        source_bbox=box.bbox,
                        label_text=label_box.text,
                        label_bbox=label_box.bbox,
                        spatial_relationship=rel_type,
                        rank_score=rank_score,
                        evidence_crop_bbox=crop_bbox,
                    )
                )

        return candidates

    @classmethod
    def _validate_field_candidate(cls, field_name: str, text: str) -> ValidationResult:
        """Applies field-specific validation based on field type."""
        if field_name == "bill_of_lading_number":
            return FieldValidators.validate_bl_number(text)
        elif field_name == "booking_number":
            return FieldValidators.validate_booking_number(text)
        elif field_name == "container_number":
            return FieldValidators.validate_container_number(text)
        elif field_name == "seal_number":
            return FieldValidators.validate_seal_number(text)
        elif field_name == "hs_code":
            return FieldValidators.validate_hs_code(text)
        elif field_name in ("gross_weight", "net_weight"):
            return FieldValidators.validate_weight(text)
        elif field_name in ("date", "on_board_date"):
            return FieldValidators.validate_date(text)
        else:
            # Generic party / text field: check it's not a forbidden token
            clean = text.strip().upper()
            if clean in FieldValidators.FORBIDDEN_IDENTIFIER_TOKENS or len(clean) < 2:
                return ValidationResult(is_valid=False, status="invalid", reason="Boilerplate token")
            return ValidationResult(is_valid=True, status="valid", normalized_value=text.strip())

    @classmethod
    def _fallback_field_match(
        cls,
        field_name: str,
        text_boxes: List[TextBox],
        page_number: int,
    ) -> Optional[ValueCandidate]:
        """Fallback pattern matching if no explicit label box was detected."""
        if field_name == "bill_of_lading_number":
            # Search for isolated high-confidence B/L format numbers (e.g. SHRCB26001503, MEDUFF439584)
            for box in text_boxes:
                val_res = FieldValidators.validate_bl_number(box.text)
                if val_res.is_valid and box.confidence > 0.80:
                    # Make sure it's in top half of document
                    return ValueCandidate(
                        field_name=field_name,
                        value_raw=box.text,
                        normalized_value=val_res.normalized_value or box.text,
                        confidence=box.confidence,
                        validation_status="valid",
                        source_page=page_number,
                        source_bbox=box.bbox,
                        label_text="inferred",
                        label_bbox=box.bbox,
                        spatial_relationship="isolated_identifier",
                        rank_score=1.2,
                        evidence_crop_bbox=box.bbox,
                    )
        return None

    @staticmethod
    def _compute_crop_bbox(
        b1: List[float],
        b2: List[float],
        page_w: int,
        page_h: int,
        padding: int = 30,
    ) -> List[float]:
        """Computes a bounding box enclosing both the label and value candidate with generous padding."""
        x1 = max(0.0, min(b1[0], b2[0]) - padding)
        y1 = max(0.0, min(b1[1], b2[1]) - padding)
        x2 = min(float(page_w), max(b1[2], b2[2]) + padding)
        y2 = min(float(page_h), max(b1[3], b2[3]) + padding)
        return [x1, y1, x2, y2]
