"""
Fallback normalizer - wraps unknown document types in canonical format v0.1
"""

from typing import Dict, Any
from .base import _generate_doc_id


def normalize_fallback_to_canonical(doc_type: str, parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback canonical format for unknown document types."""
    return {
        "schema_version": "doc.v0.1",
        "doc_type": doc_type,
        "doc_id": _generate_doc_id(doc_type, None),
        "doc_date": None,
        "period": None,
        "metadata": {
            "source_format": doc_type,
            "parser_version": "unknown",
            "warnings": parsed.get("warnings", []) + ["fallback_canonical_format"],
        },
        "business": {},
        "parties": {},
        "financials": {
            "currency": "INR",
            "subtotal": 0.0,
            "tax_breakup": {},
            "tax_total": 0.0,
            "grand_total": 0.0,
        },
        "entries": [],
        "doc_specific": parsed,
    }

