"""
Bank statement normalizer - converts bank statement documents to canonical format v0.1
"""

from typing import Dict, Any
from .base import (
    _extract_value,
    _normalize_date,
    _to_float,
    _generate_doc_id,
)
from .fallback_normalizer import normalize_fallback_to_canonical


def normalize_bank_statement_to_canonical(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert bank statement to canonical format.
    
    TODO: Implement full bank statement normalization with:
    - Account details
    - Transaction entries
    - Opening/closing balances
    - Transaction categorization
    """
    # For now, use fallback but mark as bank_statement
    canonical = normalize_fallback_to_canonical("bank_statement", parsed)
    canonical["doc_type"] = "bank_statement"
    canonical["metadata"]["source_format"] = "bank_statement"
    return canonical

