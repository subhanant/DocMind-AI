"""
Document Classification Service (Phase 3).

Classifies documents based on text cues, regex heuristics, and structure.
Supports future plug-in for ML / LLM classification.
"""
import re
from typing import Tuple

from app.db.models.document import DocumentType
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentClassifierService:
    """Classifies document type using weighted keyword matching & pattern heuristics."""

    CLASSIFICATION_RULES = {
        DocumentType.BILL_OF_LADING: {
            "primary": [
                r"\bbill\s+of\s+lading\b",
                r"\bocean\s+bill\s+of\s+lading\b",
                r"\bmultimodal\s+transport\s+bill\b",
                r"\bhouse\s+bill\s+of\s+lading\b",
                r"\bmaster\s+bill\s+of\s+lading\b",
                r"\bb/l\s*(?:no|number|\#)\b",
            ],
            "secondary": [
                r"\bport\s+of\s+loading\b",
                r"\bport\s+of\s+discharge\b",
                r"\bplace\s+of\s+receipt\b",
                r"\bplace\s+of\s+delivery\b",
                r"\bvessel\b",
                r"\bvoyage\b",
                r"\bshipper\b",
                r"\bconsignee\b",
                r"\bnotify\s+party\b",
                r"\bcontainer\s+no\b",
                r"\bseal\s+no\b",
                r"\bfreight\s+(?:prepaid|collect)\b",
                r"\bshipped\s+on\s+board\b",
                r"\bclean\s+on\s+board\b",
            ],
        },
        DocumentType.COMMERCIAL_INVOICE: {
            "primary": [
                r"\bcommercial\s+invoice\b",
                r"\btax\s+invoice\b",
                r"\bproforma\s+invoice\b",
                r"\binvoice\s*(?:no|number|\#)\b",
            ],
            "secondary": [
                r"\bunit\s+price\b",
                r"\btotal\s+amount\b",
                r"\bpayment\s+terms\b",
                r"\bincoterms\b",
                r"\bbill\s+to\b",
                r"\bship\s+to\b",
                r"\bdue\s+date\b",
                r"\bsubtotal\b",
            ],
        },
        DocumentType.PACKING_LIST: {
            "primary": [
                r"\bpacking\s+list\b",
                r"\bdelivery\s+packing\s+list\b",
                r"\bshipping\s+list\b",
            ],
            "secondary": [
                r"\bgross\s+weight\b",
                r"\bnet\s+weight\b",
                r"\bpackage\s+count\b",
                r"\bcartons\b",
                r"\bpallets\b",
                r"\bdimensions\b",
                r"\bcbm\b",
            ],
        },
        DocumentType.PURCHASE_ORDER: {
            "primary": [
                r"\bpurchase\s+order\b",
                r"\bp\.o\.\s*(?:no|number|\#)\b",
                r"\border\s+confirmation\b",
            ],
            "secondary": [
                r"\bvender\b",
                r"\bvndr\b",
                r"\bbuyer\b",
                r"\border\s+date\b",
                r"\bitem\s+description\b",
            ],
        },
        DocumentType.CERTIFICATE_OF_ORIGIN: {
            "primary": [
                r"\bcertificate\s+of\s+origin\b",
                r"\borigin\s+certificate\b",
            ],
            "secondary": [
                r"\bcountry\s+of\s+origin\b",
                r"\bchamber\s+of\s+commerce\b",
                r"\bdeclaration\s+by\s+the\s+exporter\b",
            ],
        },
    }

    @classmethod
    def classify(cls, text: str, filename: str = "") -> Tuple[DocumentType, float]:
        """
        Classifies document text and returns (DocumentType, confidence).
        """
        if not text and not filename:
            return DocumentType.UNKNOWN, 0.0

        normalized_text = (text or "").lower()
        normalized_name = (filename or "").lower()

        scores: dict[DocumentType, float] = {}

        for doc_type, rule in cls.CLASSIFICATION_RULES.items():
            type_score = 0.0

            # Check filename hints
            for pattern in rule["primary"]:
                if re.search(pattern, normalized_name):
                    type_score += 0.4
                    break

            # Check primary text patterns (high weight)
            for pattern in rule["primary"]:
                if re.search(pattern, normalized_text):
                    type_score += 0.5
                    break

            # Check secondary text patterns (cumulative up to 0.5)
            secondary_hits = 0
            for pattern in rule["secondary"]:
                if re.search(pattern, normalized_text):
                    secondary_hits += 1

            type_score += min(0.5, secondary_hits * 0.1)
            scores[doc_type] = min(1.0, type_score)

        # Find highest scoring document type
        if not scores:
            return DocumentType.UNKNOWN, 0.0

        best_type, best_score = max(scores.items(), key=lambda x: x[1])

        if best_score >= 0.4:
            logger.info("Document classified", document_type=best_type.value, confidence=round(best_score, 2))
            return best_type, round(best_score, 2)
        elif len(normalized_text) > 50:
            return DocumentType.GENERAL_DOCUMENT, 0.3
        else:
            return DocumentType.UNKNOWN, 0.0
