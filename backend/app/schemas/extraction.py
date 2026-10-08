"""
Pydantic Schemas for Document Intelligence & Bill of Lading Extraction.

Follows Phase 2 Requirements:
- Exact Section 8 Bill of Lading logical structure (BillOfLadingExtraction)
- Section 9 Field-level confidence, source text, and page references (FieldEvidence)
- Audit-preserving edit history tracking
- Backward-compatible schema definitions for legacy tests & rule extractor
"""
import re
import uuid
from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.models.document import ValidationStatus

T = TypeVar("T")


class FieldEvidence(BaseModel, Generic[T]):
    """
    Provenance and confidence envelope for an extracted field.
    Every priority field has confidence (0.0 - 1.0), raw source text citation, and page number.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: Optional[T] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_text: Optional[str] = None
    page: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "confidence": round(self.confidence, 4),
            "source_text": self.source_text,
            "page": self.page,
        }


# Legacy / ExtractedField alias
class ExtractedField(BaseModel, Generic[T]):
    value: Optional[T] = None
    confidence: float = 0.0
    source_text: Optional[str] = None
    page: Optional[int] = 1


# ─── Measurement Schemas (Weights, Volume) ───────────────────────────────────

class Measurement(BaseModel):
    """Keeps numeric values strictly separate from units (e.g. 12450.0, KGS)."""
    value: Optional[float] = None
    unit: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def parse_measurement(cls, data: Any) -> Any:
        if isinstance(data, (int, float)):
            return {"value": float(data), "unit": None}
        if isinstance(data, str):
            clean = data.strip()
            # Match number and optional unit
            m = re.search(r"([\d,]+(?:\.\d+)?)\s*([A-Za-z0-9\^3\/]+)?", clean)
            if m:
                try:
                    v = float(m.group(1).replace(",", ""))
                    u = m.group(2).strip().upper() if m.group(2) else None
                    return {"value": v, "unit": u}
                except ValueError:
                    pass
            return {"value": None, "unit": None}
        return data


# ─── Parties Schemas ─────────────────────────────────────────────────────────

class Party(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None


class Parties(BaseModel):
    shipper: Optional[Party] = None
    consignee: Optional[Party] = None
    notify_party: Optional[Party] = None


# ─── Shipment Details Schemas ────────────────────────────────────────────────

class Shipment(BaseModel):
    carrier: Optional[str] = None
    vessel_name: Optional[str] = None
    voyage_number: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    place_of_delivery: Optional[str] = None
    booking_number: Optional[str] = None


class Dates(BaseModel):
    on_board_date: Optional[str] = None


# ─── Cargo & Containers Schemas ──────────────────────────────────────────────

class Cargo(BaseModel):
    description: Optional[str] = None
    hs_code: Optional[str] = None
    number_of_packages: Optional[int] = None
    gross_weight: Optional[Measurement] = None
    net_weight: Optional[Measurement] = None
    cbm: Optional[Measurement] = None

    @field_validator("number_of_packages", mode="before")
    @classmethod
    def parse_packages(cls, v: Any) -> Optional[int]:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return int(v)
        if isinstance(v, str):
            digits = re.sub(r"[^\d]", "", v)
            return int(digits) if digits else None
        return None


class Container(BaseModel):
    container_number: Optional[str] = None
    seal_number: Optional[str] = None
    container_type: Optional[str] = None  # e.g., 20GP, 40HC, 40RF, DRY, REEFER


# ─── Freight & References Schemas ────────────────────────────────────────────

class Freight(BaseModel):
    terms: Optional[str] = None  # Prepaid, Collect
    amount: Optional[float] = None
    currency: Optional[str] = None  # USD, EUR, etc.

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            clean = re.sub(r"[^\d\.]", "", v)
            try:
                return float(clean) if clean else None
            except ValueError:
                return None
        return None


class References(BaseModel):
    invoice_number: Optional[str] = None


class DocumentMetadata(BaseModel):
    bl_number: Optional[str] = None
    bl_date: Optional[str] = None
    bl_type: Optional[str] = None  # Original, Sea Waybill, Express, Telex


# ─── Master Bill of Lading Schema (Section 8) ────────────────────────────────

class BillOfLadingExtraction(BaseModel):
    """
    Mandatory Phase 2 Bill of Lading extraction schema.
    All fields are nullable where missing; never hallucinate values.
    """
    document_type: str = "bill_of_lading"
    document_metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    parties: Parties = Field(default_factory=Parties)
    shipment: Shipment = Field(default_factory=Shipment)
    dates: Dates = Field(default_factory=Dates)
    cargo: Cargo = Field(default_factory=Cargo)
    containers: List[Container] = Field(default_factory=list)
    freight: Freight = Field(default_factory=Freight)
    references: References = Field(default_factory=References)


# ─── Backward-Compatible / Rule-Extractor Schemas ───────────────────────────

class PartyInfo(BaseModel):
    name: Optional[ExtractedField[str]] = None
    address: Optional[ExtractedField[str]] = None
    contact_phone: Optional[ExtractedField[str]] = None
    contact_email: Optional[ExtractedField[str]] = None


class ContainerInfo(BaseModel):
    container_number: Optional[ExtractedField[str]] = None
    seal_number: Optional[ExtractedField[str]] = None
    container_type: Optional[ExtractedField[str]] = None
    gross_weight: Optional[ExtractedField[str]] = None


class DangerousGoodsInfo(BaseModel):
    un_number: Optional[ExtractedField[str]] = None
    imo_class: Optional[ExtractedField[str]] = None


class BillOfLadingSchema(BaseModel):
    bl_number: Optional[ExtractedField[str]] = None
    bl_type: Optional[ExtractedField[str]] = None
    bl_status: Optional[ExtractedField[str]] = None
    bl_date: Optional[ExtractedField[str]] = None
    issue_date: Optional[ExtractedField[str]] = None
    place_of_issue: Optional[ExtractedField[str]] = None
    original_copies: Optional[ExtractedField[str]] = None
    shipper: Optional[PartyInfo] = None
    consignee: Optional[PartyInfo] = None
    notify_party: Optional[PartyInfo] = None
    booking_number: Optional[ExtractedField[str]] = None
    shipping_line: Optional[ExtractedField[str]] = None
    carrier: Optional[ExtractedField[str]] = None
    vessel_name: Optional[ExtractedField[str]] = None
    voyage_number: Optional[ExtractedField[str]] = None
    place_of_receipt: Optional[ExtractedField[str]] = None
    port_of_loading: Optional[ExtractedField[str]] = None
    port_of_discharge: Optional[ExtractedField[str]] = None
    place_of_delivery: Optional[ExtractedField[str]] = None
    final_destination: Optional[ExtractedField[str]] = None
    on_board_date: Optional[ExtractedField[str]] = None
    description: Optional[ExtractedField[str]] = None
    gross_weight: Optional[ExtractedField[str]] = None
    net_weight: Optional[ExtractedField[str]] = None
    volume: Optional[ExtractedField[str]] = None
    number_of_packages: Optional[ExtractedField[str]] = None
    marks_and_numbers: Optional[ExtractedField[str]] = None
    hs_code: Optional[ExtractedField[str]] = None
    containers: List[ContainerInfo] = Field(default_factory=list)
    freight_terms: Optional[ExtractedField[str]] = None
    freight_currency: Optional[ExtractedField[str]] = None
    invoice_number: Optional[ExtractedField[str]] = None
    purchase_order_number: Optional[ExtractedField[str]] = None
    dangerous_goods: Optional[DangerousGoodsInfo] = None


# ─── Audit / Field Edit History ──────────────────────────────────────────────

class FieldEdit(BaseModel):
    field_path: str
    original_value: Optional[Any] = None
    edited_value: Optional[Any] = None
    edited_by: Optional[str] = None
    edited_at: datetime = Field(default_factory=datetime.utcnow)


# ─── API Response Schemas ────────────────────────────────────────────────────

class ExtractionResultDetail(BaseModel):
    """Full detail returned by GET /api/documents/{id}/extraction."""
    id: uuid.UUID
    document_id: uuid.UUID
    schema_version: str = "2.0"
    extracted_json: Optional[dict[str, Any]] = None
    confidence_score: Optional[float] = None
    validation_status: ValidationStatus = ValidationStatus.PENDING
    field_evidence: Optional[dict[str, Any]] = None  # Field-level confidence map
    edit_history: List[dict[str, Any]] = Field(default_factory=list)
    processing_metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class DocumentClassificationResult(BaseModel):
    """AI Classification response model."""
    document_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class DocumentTextResponse(BaseModel):
    """Response for GET /api/documents/{id}/text."""
    document_id: uuid.UUID
    total_pages: int
    total_characters: int
    is_scanned: bool
    ocr_used: bool
    pages: List[dict[str, Any]]
    full_text: str


class ProcessingStatusStage(BaseModel):
    name: str
    status: str  # "completed" | "in_progress" | "pending" | "failed"
    message: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class ProcessingStatusResponse(BaseModel):
    """Response for GET /api/documents/{id}/processing-status."""
    document_id: uuid.UUID
    overall_status: str
    progress_percentage: int
    current_stage: str
    stages: List[ProcessingStatusStage]
    error_message: Optional[str] = None
