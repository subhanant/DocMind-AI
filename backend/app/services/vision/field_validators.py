"""
Field-Specific Validation and Candidate Scoring Engine.

Validates and scores candidate values for shipping & logistics fields:
- B/L Number
- Booking Number
- Container Number (ISO 6346 checksum & format)
- Seal Number
- HS Code
- Gross / Net Weight
- Dates
- Vessel / Voyage
- Parties (Shipper / Consignee / Notify)

Strictly filters out boilerplate legal noise and false positive labels (e.g. "Received").
"""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ValidationResult:
    is_valid: bool
    status: str  # "valid", "invalid", "unreadable", "missing"
    normalized_value: Optional[Any] = None
    confidence_delta: float = 0.0
    reason: str = ""


class FieldValidators:
    """Rigorous field validators providing validation status and normalized representations."""

    # Common boilerplate text that must NEVER be accepted as an identifier or name
    FORBIDDEN_IDENTIFIER_TOKENS = {
        "RECEIVED", "DRAFT", "ORIGINAL", "COPY", "NON-NEGOTIABLE", "NEGOTIABLE",
        "PAGE", "TERMS", "CONDITIONS", "CLAUSE", "SHIPPED", "BOARD", "NUMBER",
        "NONE", "NULL", "UNKNOWN", "APPARENT", "GOOD", "ORDER", "TOTAL",
        "CONTAINER", "SEAL", "VESSEL", "VOYAGE", "PORT", "PLACE", "DATE",
        "FREIGHT", "PREPAID", "COLLECT", "MERCHANT", "CARRIER", "AGENT",
        "WEIGHT", "CODE", "SAID TO CONTAIN", "DESCRIPTION OF GOODS",
        "BAGS", "BAG(S)", "CONTAINERS", "FCL/FCL", "STC", "DELIVERY AGENT",
        "MARKS & NUMBERS", "PARTICULARS", "DECLARED", "BOOKING", "BILL",
        "LADING", "INVOICE", "PACKING", "DISCHARGE", "LOADING", "RECEIPT",
        "DELIVERY", "DESTINATION", "ISSUE", "TYPE", "REFERENCE", "NOTIFY",
        "CONSIGNEE", "SHIPPER",
    }

    @classmethod
    def validate_bl_number(cls, text: str) -> ValidationResult:
        """Validates Bill of Lading Number format."""
        if not text:
            return ValidationResult(is_valid=False, status="missing", reason="Empty value")

        clean = text.strip()
        clean_upper = clean.upper()

        # Reject pure boilerplate words
        words = [w for w in re.split(r"[\s\-_/:.]+", clean_upper) if w]
        if not words:
            return ValidationResult(is_valid=False, status="missing", reason="Empty value")

        if any(w in cls.FORBIDDEN_IDENTIFIER_TOKENS for w in words) and not re.search(r"\d", clean_upper):
            return ValidationResult(
                is_valid=False,
                status="invalid",
                reason=f"Matched document boilerplate token '{clean}' instead of real identifier",
            )

        # Standard B/L numbers are alphanumeric containing digits
        # Common formats: SHRCB26001503, MEDUFF439584, MSCU9283741, MEDU987654321, RCL12345, COSU61234567, 123456789
        m = re.search(r"\b([A-Z0-9\-_/]{5,25})\b", clean_upper)
        if m:
            val = m.group(1)
            # Ensure it is not a forbidden token
            if val in cls.FORBIDDEN_IDENTIFIER_TOKENS:
                return ValidationResult(is_valid=False, status="invalid", reason=f"Forbidden token '{val}'")

            has_letters = bool(re.search(r"[A-Z]", val))
            has_digits = bool(re.search(r"\d", val))

            # Valid B/L numbers must contain digits!
            if has_letters and has_digits and len(val) >= 6:
                return ValidationResult(
                    is_valid=True,
                    status="valid",
                    normalized_value=val,
                    confidence_delta=0.15,
                    reason="Valid alphanumeric B/L number format",
                )
            elif has_digits and len(val) >= 6:
                return ValidationResult(
                    is_valid=True,
                    status="valid",
                    normalized_value=val,
                    confidence_delta=0.08,
                    reason="Numeric B/L number format",
                )

        return ValidationResult(is_valid=False, status="invalid", reason="Malformed B/L number (requires digits)")

    @classmethod
    def validate_booking_number(cls, text: str) -> ValidationResult:
        """Validates Booking / Reference Number."""
        if not text:
            return ValidationResult(is_valid=False, status="missing", reason="Empty value")
        clean = text.strip().upper()
        if clean in cls.FORBIDDEN_IDENTIFIER_TOKENS:
            return ValidationResult(is_valid=False, status="invalid", reason="Boilerplate token")
        m = re.search(r"\b([A-Z0-9\-_/]{4,25})\b", clean)
        if m:
            return ValidationResult(
                is_valid=True,
                status="valid",
                normalized_value=m.group(1),
                confidence_delta=0.05,
            )
        return ValidationResult(is_valid=False, status="invalid", reason="Malformed booking number")

    @classmethod
    def validate_container_number(cls, text: str) -> ValidationResult:
        """
        Validates ISO 6346 Container Number:
        4 uppercase letters (last letter usually U, J, or Z) + 6 serial digits + 1 check digit.
        Example: CAAU7671123, REGU5167196, TXGU6767410.
        """
        if not text:
            return ValidationResult(is_valid=False, status="missing", reason="Empty value")

        clean = re.sub(r"[\s\-_]+", "", text.strip().upper())
        # Check standard 4 letters + 7 digits
        if re.match(r"^[A-Z]{4}\d{7}$", clean):
            # ISO 6346 check digit algorithm
            check_digit_valid = cls._iso6346_check_digit(clean)
            return ValidationResult(
                is_valid=True,
                status="valid",
                normalized_value=clean,
                confidence_delta=0.10 if check_digit_valid else 0.05,
                reason="Standard ISO 6346 container number",
            )
        elif re.match(r"^[A-Z]{3,4}\d{6,8}$", clean):
            return ValidationResult(
                is_valid=True,
                status="valid",
                normalized_value=clean,
                confidence_delta=0.03,
                reason="Alphanumeric container code",
            )
        return ValidationResult(is_valid=False, status="invalid", reason="Invalid container format")

    @staticmethod
    def _iso6346_check_digit(code: str) -> bool:
        """Computes ISO 6346 container check digit."""
        if len(code) != 11:
            return False
        char_map = {
            'A': 10, 'B': 12, 'C': 13, 'D': 14, 'E': 15, 'F': 16, 'G': 17, 'H': 18, 'I': 19,
            'J': 20, 'K': 21, 'L': 23, 'M': 24, 'N': 25, 'O': 26, 'P': 27, 'Q': 28, 'R': 29,
            'S': 30, 'T': 31, 'U': 32, 'V': 34, 'W': 35, 'X': 36, 'Y': 37, 'Z': 38,
        }
        total = 0
        for i in range(10):
            c = code[i]
            val = char_map[c] if c in char_map else int(c)
            total += val * (2 ** i)
        expected_check = (total % 11) % 10
        actual_check = int(code[10])
        return expected_check == actual_check

    @classmethod
    def validate_seal_number(cls, text: str) -> ValidationResult:
        """Validates Seal Number."""
        if not text:
            return ValidationResult(is_valid=False, status="missing", reason="Empty value")
        clean = text.strip().upper()
        if clean in cls.FORBIDDEN_IDENTIFIER_TOKENS:
            return ValidationResult(is_valid=False, status="invalid", reason="Boilerplate token")
        m = re.search(r"\b([A-Z0-9\-_/]{4,20})\b", clean)
        if m:
            return ValidationResult(
                is_valid=True,
                status="valid",
                normalized_value=m.group(1),
                confidence_delta=0.05,
            )
        return ValidationResult(is_valid=False, status="invalid", reason="Malformed seal number")

    @classmethod
    def validate_hs_code(cls, text: str) -> ValidationResult:
        """Validates Harmonized System (HS) Code (6 to 10 digits)."""
        if not text:
            return ValidationResult(is_valid=False, status="missing", reason="Empty value")
        clean_upper = text.strip().upper()
        if any(bad in clean_upper for bad in ["SO NUMBER", "B/L", "BOOKING", "INVOICE", "CONTAINER", "SEAL"]):
            return ValidationResult(is_valid=False, status="invalid", reason="Contains conflicting identifier prefix")
        clean = re.sub(r"[^\d]", "", text)
        if 6 <= len(clean) <= 10:
            return ValidationResult(
                is_valid=True,
                status="valid",
                normalized_value=clean,
                confidence_delta=0.08,
                reason="Valid 6-10 digit HS Code",
            )
        return ValidationResult(is_valid=False, status="invalid", reason="Invalid HS code length")

    @classmethod
    def validate_weight(cls, text: str) -> ValidationResult:
        """Validates weight string (e.g. 135000.00 KG, 27,450.000 KGS, 101376.0 KGS)."""
        if not text:
            return ValidationResult(is_valid=False, status="missing", reason="Empty value")
        if "HS CODE" in text.upper():
            return ValidationResult(is_valid=False, status="invalid", reason="Matched HS code instead of weight")
        # Match number and unit
        m = re.search(r"([\d,]+(?:\.\d+)?)\s*([A-Za-z]+)?", text)
        if m:
            raw_num = m.group(1).replace(",", "")
            try:
                val = float(raw_num)
                unit = (m.group(2) or "KG").upper()
                if unit in ("KGS", "KGM", "KILOS"):
                    unit = "KG"
                elif unit in ("LBS", "POUNDS"):
                    unit = "LBS"
                return ValidationResult(
                    is_valid=True,
                    status="valid",
                    normalized_value={"value": val, "unit": unit},
                    confidence_delta=0.06,
                )
            except ValueError:
                pass
        return ValidationResult(is_valid=False, status="invalid", reason="Malformed weight")

    @classmethod
    def validate_date(cls, text: str) -> ValidationResult:
        """Validates and normalizes date string to ISO YYYY-MM-DD."""
        if not text:
            return ValidationResult(is_valid=False, status="missing", reason="Empty value")

        clean = text.strip()
        # Common date formats in shipping documents:
        # DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD-Mon-YYYY (16-Sep-2026), 22/09/2026
        patterns = [
            (r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", "%d/%m/%Y"),
            (r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", "%Y-%m-%d"),
            (r"(\d{1,2})[-/\s]([A-Za-z]{3,9})[-/\s](\d{4})", "%d-%b-%Y"),
        ]

        for pat, fmt in patterns:
            m = re.search(pat, clean)
            if m:
                matched_str = m.group(0).replace("/", "-").replace(".", "-")
                try:
                    dt = datetime.strptime(matched_str, fmt.replace("/", "-"))
                    return ValidationResult(
                        is_valid=True,
                        status="valid",
                        normalized_value=dt.strftime("%Y-%m-%d"),
                        confidence_delta=0.08,
                        reason="Normalized ISO date",
                    )
                except ValueError:
                    pass

        return ValidationResult(is_valid=False, status="invalid", reason="Unrecognized date format")
