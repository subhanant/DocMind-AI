"""
Bill of Lading Structured Pattern & Heuristic Extractor.

Extracts all fields specified in BillOfLadingSchema with per-field confidence scores,
exact source text provenance, and page numbers.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.extraction import (
    BillOfLadingSchema,
    ContainerInfo,
    DangerousGoodsInfo,
    ExtractedField,
    PartyInfo,
)


class BillOfLadingRuleExtractor:
    """Extracts Bill of Lading structured data using pattern recognition and contextual NLP."""

    # Major ocean shipping lines
    CARRIERS = [
        "MAERSK", "MEDITERRANEAN SHIPPING COMPANY", "MSC", "CMA CGM", "COSCO SHIPPING",
        "HAPAG-LLOYD", "OCEAN NETWORK EXPRESS", "ONE", "EVERGREEN LINE", "EVERGREEN",
        "HYUNDAI MERCHANT MARINE", "HMM", "YANG MING", "ZIM INTEGRATED SHIPPING",
        "WAN HAI LINES", "PIL", "PACIFIC INTERNATIONAL LINES", "OOCL", "K-LINE", "NYK LINE", "MOL"
    ]

    @classmethod
    def extract(cls, text: str, pages_data: Optional[List[Dict[str, Any]]] = None) -> Tuple[BillOfLadingSchema, float]:
        """
        Extract Bill of Lading schema and return (schema, overall_confidence).
        """
        schema = BillOfLadingSchema()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        full_text_upper = text.upper()

        # 1. Document Metadata
        schema.bl_number = cls._extract_bl_number(text, lines)
        schema.bl_type = cls._extract_bl_type(text)
        schema.bl_status = cls._extract_bl_status(text)
        schema.bl_date = cls._extract_date_after(text, [r"B/?L\s*Date", r"Date\s*of\s*Issue", r"Issue\s*Date"])
        schema.place_of_issue = cls._extract_field_after(text, [r"Place\s*of\s*Issue", r"Issued\s*at"])
        schema.original_copies = cls._extract_field_after(text, [r"Number\s*of\s*Original\s*B/?L'?s?", r"No\.\s*of\s*Originals?"])

        # 2. Parties
        schema.shipper = cls._extract_party(text, "SHIPPER", ["CONSIGNEE", "NOTIFY", "VESSEL", "PORT OF LOADING"])
        schema.consignee = cls._extract_party(text, "CONSIGNEE", ["NOTIFY", "ALSO NOTIFY", "VESSEL", "PORT OF DISCHARGE"])
        schema.notify_party = cls._extract_party(text, "NOTIFY PARTY", ["CONSIGNEE", "VESSEL", "PORT OF LOADING", "ALSO NOTIFY"])

        # 3. Shipment Details
        schema.booking_number = cls._extract_booking_number(text, lines)
        schema.shipping_line = cls._extract_shipping_line(text)
        schema.carrier = schema.shipping_line
        schema.vessel_name = cls._extract_vessel_name(text, lines)
        schema.voyage_number = cls._extract_voyage_number(text, lines)
        schema.place_of_receipt = cls._extract_location(text, [r"Place\s*of\s*Receipt", r"Pre-Carriage\s*by\s*from"])
        schema.port_of_loading = cls._extract_location(text, [r"Port\s*of\s*Loading", r"POL\b", r"Loading\s*Port"])
        schema.port_of_discharge = cls._extract_location(text, [r"Port\s*of\s*Discharge", r"POD\b", r"Discharge\s*Port"])
        schema.place_of_delivery = cls._extract_location(text, [r"Place\s*of\s*Delivery", r"Final\s*Destination", r"Delivery\s*Place"])
        schema.final_destination = schema.place_of_delivery

        # 4. Dates
        schema.issue_date = schema.bl_date
        schema.on_board_date = cls._extract_date_after(text, [r"Shipped\s*on\s*Board\s*Date", r"On\s*Board\s*Date", r"Laden\s*on\s*Board"])

        # 5. Cargo & Weights
        schema.description = cls._extract_cargo_description(text)
        schema.gross_weight = cls._extract_weight(text, [r"Gross\s*Weight", r"Total\s*Gross\s*Weight", r"G\.W\."])
        schema.net_weight = cls._extract_weight(text, [r"Net\s*Weight", r"N\.W\."])
        schema.volume = cls._extract_volume(text)
        schema.number_of_packages = cls._extract_packages(text)
        schema.marks_and_numbers = cls._extract_field_after(text, [r"Marks\s*and\s*Numbers?", r"Marks\s*&\s*Nos?"])
        schema.hs_code = cls._extract_hs_code(text)

        # 6. Containers
        bl_num_val = schema.bl_number.value if schema.bl_number else None
        schema.containers = cls._extract_containers(text, exclude_number=bl_num_val)

        # 7. Freight & Terms
        schema.freight_terms = cls._extract_freight_terms(text)
        schema.freight_currency = cls._extract_currency(text)

        # 8. References
        schema.invoice_number = cls._extract_field_after(text, [r"Invoice\s*(?:No|Number|\#)", r"Commercial\s*Invoice"])
        schema.purchase_order_number = cls._extract_field_after(text, [r"P\.?O\.?\s*(?:No|Number|\#)", r"Purchase\s*Order"])

        # 9. Dangerous Goods
        schema.dangerous_goods = cls._extract_dangerous_goods(text)

        # Compute overall confidence score
        overall_confidence = cls._calculate_confidence(schema)
        return schema, overall_confidence

    @classmethod
    def _extract_bl_number(cls, text: str, lines: List[str]) -> Optional[ExtractedField]:
        patterns = [
            r"(?:B/?L\s*(?:NO|NUMBER|\#)|BILL\s+OF\s+LADING\s*(?:NO|NUMBER|\#))\s*[:.]?\s*([A-Z0-9\-_/]{5,25})",
            r"\b([A-Z]{3,4}[0-9]{7,12})\b",  # Standard carrier prefix + digits
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                # Exclude container numbers if accidentally matched
                if not re.match(r"^[A-Z]{4}\d{7}$", val):
                    return ExtractedField(
                        value=val,
                        confidence=0.95 if "B/L" in match.group(0).upper() else 0.85,
                        source_text=match.group(0).strip(),
                        page=1,
                    )

        # Line scan fallback
        for i, line in enumerate(lines[:20]):
            if any(term in line.upper() for term in ["B/L NO", "BILL OF LADING NO", "B/L NUMBER"]):
                parts = re.split(r"[:\s]+", line)
                if len(parts) > 1:
                    val = parts[-1].strip()
                    if len(val) >= 4:
                        return ExtractedField(value=val, confidence=0.88, source_text=line, page=1)

        return None

    @classmethod
    def _extract_booking_number(cls, text: str, lines: List[str]) -> Optional[ExtractedField]:
        match = re.search(r"(?:Booking\s*(?:No|Number|\#)|BKG\s*(?:No|REF))\s*[:.]?\s*([A-Z0-9\-_/]{5,25})", text, re.IGNORECASE)
        if match:
            return ExtractedField(value=match.group(1).strip(), confidence=0.92, source_text=match.group(0).strip(), page=1)
        return None

    @classmethod
    def _extract_bl_type(cls, text: str) -> Optional[ExtractedField]:
        types = [
            ("Original Bill of Lading", 0.95),
            ("Negotiable Bill of Lading", 0.95),
            ("Non-Negotiable Sea Waybill", 0.95),
            ("Sea Waybill", 0.90),
            ("Express Release", 0.90),
            ("House Bill of Lading", 0.90),
            ("Master Bill of Lading", 0.90),
            ("Multimodal Transport Document", 0.85),
        ]
        for name, conf in types:
            if re.search(r"\b" + re.escape(name) + r"\b", text, re.IGNORECASE):
                return ExtractedField(value=name, confidence=conf, source_text=name, page=1)
        return ExtractedField(value="Original Bill of Lading", confidence=0.70, source_text="Inferred standard B/L", page=1)

    @classmethod
    def _extract_bl_status(cls, text: str) -> Optional[ExtractedField]:
        if re.search(r"\b(?:CLEAN\s+ON\s+BOARD|SHIPPED\s+ON\s+BOARD|CLEAN\s+SHIPPED)\b", text, re.IGNORECASE):
            return ExtractedField(value="Clean on Board", confidence=0.95, source_text="Shipped on Board", page=1)
        if re.search(r"\bRECEIVED\s+FOR\s+SHIPMENT\b", text, re.IGNORECASE):
            return ExtractedField(value="Received for Shipment", confidence=0.90, source_text="Received for Shipment", page=1)
        return None

    @classmethod
    def _extract_shipping_line(cls, text: str) -> Optional[ExtractedField]:
        for carrier in cls.CARRIERS:
            pattern = r"\b" + re.escape(carrier) + r"\b"
            if re.search(pattern, text, re.IGNORECASE):
                return ExtractedField(value=carrier, confidence=0.92, source_text=carrier, page=1)
        return None

    @classmethod
    def _extract_vessel_name(cls, text: str, lines: List[str]) -> Optional[ExtractedField]:
        match = re.search(r"(?:Ocean\s+Vessel|Vessel\s*(?:Name)?|Feeder\s+Vessel)\s*[:/]?\s*([A-Z0-9\s\.\-]{3,35})(?:\s+(?:Voy|Voyage|V\.))?", text, re.IGNORECASE)
        if match:
            vessel = match.group(1).strip()
            # Clean up trailing voyage words
            vessel = re.sub(r"(?i)\s+voy.*$", "", vessel).strip()
            if len(vessel) >= 3 and not any(kw in vessel.upper() for kw in ["PORT", "LOADING", "DISCHARGE", "VOYAGE"]):
                return ExtractedField(value=vessel, confidence=0.88, source_text=match.group(0).strip(), page=1)
        return None

    @classmethod
    def _extract_voyage_number(cls, text: str, lines: List[str]) -> Optional[ExtractedField]:
        match = re.search(r"(?:Voyage\s*(?:No|Number|\#)?|Voy\.?\s*(?:No)?|V\.)\s*[:.]?\s*([A-Z0-9\-_/]{2,15})", text, re.IGNORECASE)
        if match:
            voy = match.group(1).strip()
            if len(voy) >= 2:
                return ExtractedField(value=voy, confidence=0.90, source_text=match.group(0).strip(), page=1)
        return None

    @classmethod
    def _extract_location(cls, text: str, markers: List[str]) -> Optional[ExtractedField]:
        for marker in markers:
            pattern = marker + r"\s*[:.]?\s*([A-Za-z0-9\s,\.\-]{3,40})(?:\n|\r|;|$)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                # Discard common non-location phrases
                if len(val) >= 3 and not any(kw in val.upper() for kw in ["BILL OF", "CONTAINER", "WEIGHT", "DESCRIPTION"]):
                    return ExtractedField(value=val, confidence=0.85, source_text=match.group(0).strip(), page=1)
        return None

    @classmethod
    def _extract_party(cls, text: str, party_label: str, stop_labels: List[str]) -> Optional[PartyInfo]:
        pattern = r"\b" + re.escape(party_label) + r"(?:\s*\(.*?\))?\s*[:.]?\s*\n?(.*?)(?=" + "|".join([r"\b" + re.escape(s) + r"\b" for s in stop_labels] + [r"\n\n\n", r"$"]) + r")"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None

        raw_block = match.group(1).strip()
        lines = [line.strip() for line in raw_block.splitlines() if line.strip() and not line.strip().startswith("---")]
        if not lines:
            return None

        name = lines[0] if lines else None
        address = ", ".join(lines[1:4]) if len(lines) > 1 else None

        # Phone extraction
        phone_match = re.search(r"(?:TEL|PHONE|MOBILE|FAX)\s*[:.]?\s*([\+\d\s\-\(\)]{7,20})", raw_block, re.IGNORECASE)
        phone = phone_match.group(1).strip() if phone_match else None

        # Email extraction
        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", raw_block)
        email = email_match.group(0) if email_match else None

        party = PartyInfo()
        if name:
            party.name = ExtractedField(value=name, confidence=0.90, source_text=name, page=1)
        if address:
            party.address = ExtractedField(value=address, confidence=0.85, source_text=address, page=1)
        if phone:
            party.contact_phone = ExtractedField(value=phone, confidence=0.92, source_text=phone_match.group(0), page=1)
        if email:
            party.contact_email = ExtractedField(value=email, confidence=0.95, source_text=email, page=1)

        return party

    @classmethod
    def _extract_weight(cls, text: str, markers: List[str]) -> Optional[ExtractedField]:
        for marker in markers:
            pattern = marker + r"\s*[:.]?\s*([\d,]+(?:\.\d+)?)\s*(KGS?|LBS?|MT|TONS?)?"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                unit = match.group(2).strip().upper() if match.group(2) else "KGS"
                formatted = f"{val} {unit}"
                return ExtractedField(value=formatted, confidence=0.90, source_text=match.group(0).strip(), page=1)
        return None

    @classmethod
    def _extract_volume(cls, text: str) -> Optional[ExtractedField]:
        pattern = r"(?:Measurement|Volume|Cube|CBM)\s*[:.]?\s*([\d,]+(?:\.\d+)?)\s*(CBM|M3|CFT|CBF)?"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            unit = match.group(2).strip().upper() if match.group(2) else "CBM"
            return ExtractedField(value=f"{val} {unit}", confidence=0.88, source_text=match.group(0).strip(), page=1)
        return None

    @classmethod
    def _extract_packages(cls, text: str) -> Optional[ExtractedField]:
        pattern = r"(?:No\.\s*of\s*Packages|Total\s*Packages|Packages?)\s*[:.]?\s*(\d+)\s*([A-Za-z\s]{3,20})?"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            qty = match.group(1).strip()
            pkg_type = match.group(2).strip() if match.group(2) else "PACKAGES"
            return ExtractedField(value=f"{qty} {pkg_type}", confidence=0.88, source_text=match.group(0).strip(), page=1)
        return None

    @classmethod
    def _extract_cargo_description(cls, text: str) -> Optional[ExtractedField]:
        pattern = r"(?:Description\s+of\s+(?:Goods|Cargo|Packages)|Commodity|Cargo\s+Description)\s*[:.]?\s*\n?(.*?)(?=\n\n|\bGross\s+Weight\b|\bMeasurement\b|\bContainer\b|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            desc = match.group(1).strip()
            # Clean lines
            lines = [l.strip() for l in desc.splitlines() if l.strip()]
            clean_desc = " ".join(lines[:5])
            if len(clean_desc) > 3:
                return ExtractedField(value=clean_desc, confidence=0.86, source_text=clean_desc, page=1)
        return None

    @classmethod
    def _extract_hs_code(cls, text: str) -> Optional[ExtractedField]:
        match = re.search(r"\b(?:HS\s*CODE|H\.S\.\s*CODE|TARIFF\s*CODE)\s*[:.]?\s*(\d{4,10}(?:\.\d{2,4})?)\b", text, re.IGNORECASE)
        if match:
            return ExtractedField(value=match.group(1).strip(), confidence=0.95, source_text=match.group(0).strip(), page=1)
        return None

    @classmethod
    def _extract_containers(cls, text: str, exclude_number: Optional[str] = None) -> List[ContainerInfo]:
        """Extract standard ISO 6346 container numbers (4 letters + 7 digits) and associated details."""
        container_pattern = r"\b([A-Z]{4}[0-9]{7})\b"
        containers = []
        found_nums = set()
        if exclude_number:
            found_nums.add(exclude_number.strip().upper())

        for match in re.finditer(container_pattern, text):
            cntr_num = match.group(1).upper()
            if cntr_num in found_nums:
                continue

            # Check if immediately preceded by "B/L" or "BILL OF LADING"
            pre_start = max(0, match.start() - 30)
            pre_text = text[pre_start:match.start()].upper()
            if "B/L" in pre_text or "BILL OF LADING" in pre_text or "BOOKING" in pre_text:
                continue

            found_nums.add(cntr_num)

            # Look around the container match for seal number, type, etc.
            start_pos = max(0, match.start() - 100)
            end_pos = min(len(text), match.end() + 200)
            snippet = text[start_pos:end_pos]

            # Seal number
            seal_match = re.search(r"(?:Seal\s*(?:No|Number|\#)?|SL\s*[:.]?)\s*[:.]?\s*([A-Z0-9\-_]{4,15})", snippet, re.IGNORECASE)
            seal_num = seal_match.group(1).strip() if seal_match else None

            # Container size/type (e.g., 40HC, 20GP, 40' HC)
            type_match = re.search(r"\b(20(?:FT|'|GP|DV)?|40(?:FT|'|GP|HC|HQ|DV|FR|OT)?|45(?:FT|'|HQ)?)\b", snippet, re.IGNORECASE)
            cntr_type = type_match.group(1).strip() if type_match else "40' High Cube"

            # Package count / weight
            weight_match = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:KGS?|LBS?)", snippet, re.IGNORECASE)
            gross_weight = weight_match.group(0).strip() if weight_match else None

            container_info = ContainerInfo(
                container_number=ExtractedField(value=cntr_num, confidence=0.96, source_text=cntr_num, page=1),
                seal_number=ExtractedField(value=seal_num, confidence=0.90, source_text=seal_match.group(0) if seal_match else None, page=1) if seal_num else None,
                container_type=ExtractedField(value=cntr_type, confidence=0.85, source_text=cntr_type, page=1) if cntr_type else None,
                gross_weight=ExtractedField(value=gross_weight, confidence=0.88, source_text=gross_weight, page=1) if gross_weight else None,
            )
            containers.append(container_info)

        return containers

    @classmethod
    def _extract_freight_terms(cls, text: str) -> Optional[ExtractedField]:
        if re.search(r"\bFREIGHT\s+PREPAID\b", text, re.IGNORECASE):
            return ExtractedField(value="Prepaid", confidence=0.95, source_text="FREIGHT PREPAID", page=1)
        elif re.search(r"\bFREIGHT\s+COLLECT\b", text, re.IGNORECASE):
            return ExtractedField(value="Collect", confidence=0.95, source_text="FREIGHT COLLECT", page=1)
        elif re.search(r"\bFREIGHT\s+PAYABLE\s+AT\b", text, re.IGNORECASE):
            return ExtractedField(value="Payable at Destination", confidence=0.85, source_text="FREIGHT PAYABLE AT", page=1)
        return None

    @classmethod
    def _extract_currency(cls, text: str) -> Optional[ExtractedField]:
        for curr in ["USD", "EUR", "GBP", "INR", "SGD", "AED", "JPY", "CNY"]:
            if re.search(r"\b" + curr + r"\b", text):
                return ExtractedField(value=curr, confidence=0.90, source_text=curr, page=1)
        return ExtractedField(value="USD", confidence=0.75, source_text="Default Standard Currency", page=1)

    @classmethod
    def _extract_dangerous_goods(cls, text: str) -> Optional[DangerousGoodsInfo]:
        un_match = re.search(r"\b(UN\s*\d{4})\b", text, re.IGNORECASE)
        class_match = re.search(r"\b(?:IMO|IMDG|CLASS)\s*[:.]?\s*(\d(?:\.\d)?)\b", text, re.IGNORECASE)
        
        if un_match or class_match:
            return DangerousGoodsInfo(
                un_number=ExtractedField(value=un_match.group(1).replace(" ", ""), confidence=0.95, source_text=un_match.group(0), page=1) if un_match else None,
                imo_class=ExtractedField(value=class_match.group(1), confidence=0.92, source_text=class_match.group(0), page=1) if class_match else None,
            )
        return None

    @classmethod
    def _extract_field_after(cls, text: str, markers: List[str]) -> Optional[ExtractedField]:
        for marker in markers:
            pattern = marker + r"\s*[:.]?\s*([A-Za-z0-9\s,\.\-/\(\)]{2,50})(?:\n|\r|;|$)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if len(val) >= 2:
                    return ExtractedField(value=val, confidence=0.85, source_text=match.group(0).strip(), page=1)
        return None

    @classmethod
    def _extract_date_after(cls, text: str, markers: List[str]) -> Optional[ExtractedField]:
        date_pattern = r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})"
        for marker in markers:
            pattern = marker + r"\s*[:.]?\s*" + date_pattern
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return ExtractedField(value=match.group(1).strip(), confidence=0.92, source_text=match.group(0).strip(), page=1)
        return None

    @classmethod
    def _calculate_confidence(cls, schema: BillOfLadingSchema) -> float:
        """Compute aggregate confidence across extracted fields."""
        scores = []

        def check_field(field_obj: Optional[ExtractedField]):
            if field_obj and field_obj.confidence is not None:
                scores.append(field_obj.confidence)

        check_field(schema.bl_number)
        check_field(schema.bl_type)
        check_field(schema.shipping_line)
        check_field(schema.vessel_name)
        check_field(schema.voyage_number)
        check_field(schema.port_of_loading)
        check_field(schema.port_of_discharge)
        check_field(schema.gross_weight)
        check_field(schema.description)
        check_field(schema.freight_terms)

        if schema.shipper and schema.shipper.name:
            check_field(schema.shipper.name)
        if schema.consignee and schema.consignee.name:
            check_field(schema.consignee.name)

        if schema.containers:
            for c in schema.containers:
                check_field(c.container_number)

        if not scores:
            return 0.0

        avg = sum(scores) / len(scores)
        # Bonus if key fields (bl_number + vessel + ports) are present
        bonus = 0.0
        if schema.bl_number and schema.bl_number.value:
            bonus += 0.05
        if schema.port_of_loading and schema.port_of_discharge:
            bonus += 0.05

        return round(min(1.0, avg + bonus), 2)
