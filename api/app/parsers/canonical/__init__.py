"""
Canonical JSON Format v0.1 - Modular Normalizers

Each document type has its own normalizer module for better organization and maintainability.
"""

from .base import (
    _extract_value,
    _extract_state_code,
    _normalize_date,
    _to_float,
    _build_tax_breakup_from_taxes,
    _generate_doc_id,
)

from .invoice_normalizer import normalize_invoice_to_canonical
from .register_normalizer import (
    normalize_purchase_register_to_canonical,
    normalize_sales_register_to_canonical,
)
from .gstr3b_normalizer import normalize_gstr3b_to_canonical
from .gstr2b_normalizer import normalize_gstr2b_to_canonical
from .gstr1_normalizer import normalize_gstr1_to_canonical
from .bank_statement_normalizer import normalize_bank_statement_to_canonical


def normalize_to_canonical(doc_type: str, parsed_data: dict) -> dict:
    """
    Convert any parsed document to canonical JSON format v0.1.
    
    This is the main entry point - it routes to the appropriate normalizer
    based on document type.
    
    Args:
        doc_type: Document type (invoice, purchase_register, sales_register, etc.)
        parsed_data: Parsed document data in original format
    
    Returns:
        Canonical JSON structure
    """
    # Normalize doc_type for matching (case-insensitive, handle variations)
    doc_type_lower = doc_type.lower() if doc_type else ""
    
    if doc_type_lower in ("invoice", "gst_invoice"):
        return normalize_invoice_to_canonical(parsed_data)
    elif doc_type_lower == "purchase_register":
        return normalize_purchase_register_to_canonical(parsed_data)
    elif doc_type_lower == "sales_register":
        return normalize_sales_register_to_canonical(parsed_data)
    elif doc_type_lower in ("gstr", "gstr3b", "gstr-3b"):
        return normalize_gstr3b_to_canonical(parsed_data)
    elif doc_type_lower in ("gstr2b", "gstr-2b"):
        return normalize_gstr2b_to_canonical(parsed_data)
    elif doc_type_lower in ("gstr1", "gstr-1"):
        return normalize_gstr1_to_canonical(parsed_data)
    elif doc_type_lower == "bank_statement":
        return normalize_bank_statement_to_canonical(parsed_data)
    else:
        # Fallback: wrap unknown types in canonical structure
        from .fallback_normalizer import normalize_fallback_to_canonical
        return normalize_fallback_to_canonical(doc_type, parsed_data)

