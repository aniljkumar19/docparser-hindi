"""
GSTR-1 normalizer - converts GSTR-1 documents to canonical format v0.1
"""

from typing import Dict, Any
from .gstr3b_normalizer import normalize_gstr3b_to_canonical


def normalize_gstr1_to_canonical(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert GSTR-1 to canonical format.
    
    For now, GSTR-1 uses similar structure to GSTR-3B, so we reuse that logic.
    In the future, this can be extended with GSTR-1 specific fields.
    """
    # Use GSTR-3B normalizer as base, then adjust doc_type
    canonical = normalize_gstr3b_to_canonical(parsed)
    canonical["doc_type"] = "gstr1"
    canonical["metadata"]["source_format"] = "gstr1"
    canonical["doc_specific"]["gstr_form"] = "GSTR-1"
    return canonical

