"""
GSTR-3B Validator

Validates canonical format gstr3b documents.
Returns structured validation issues with codes, levels, and metadata.
"""

from typing import Dict, Any, List


def _f(x: Any) -> float:
    """Safely convert value to float."""
    try:
        return float(x or 0.0)
    except Exception:
        return 0.0


def validate_gstr3b(doc: Dict[str, Any], tolerance: float = 1.0) -> List[Dict[str, Any]]:
    """
    Validate canonical gstr3b doc (schema_version='doc.v0.1', doc_type='gstr3b').
    
    Focus: entries vs financials consistency.
    
    Args:
        doc: Canonical format gstr3b document
        tolerance: Tolerance for numeric comparisons (default: 1.0)
    
    Returns:
        List of validation issues, each with:
        {
            "code": "...",
            "level": "warning|error",
            "message": "...",
            "meta": {...}
        }
    """
    issues: List[Dict[str, Any]] = []
    
    financials = doc.get("financials") or {}
    entries = doc.get("entries") or []
    
    subtotal_canon = _f(financials.get("subtotal"))
    tb = financials.get("tax_breakup") or {}
    cgst_canon = _f(tb.get("cgst"))
    sgst_canon = _f(tb.get("sgst"))
    igst_canon = _f(tb.get("igst"))
    cess_canon = _f(tb.get("cess"))
    tax_total_canon = _f(financials.get("tax_total"))
    grand_total_canon = _f(financials.get("grand_total"))
    
    # Aggregate from entries (OUTWARD + REVERSE_CHARGE)
    subtotal_calc = 0.0
    cgst_calc = sgst_calc = igst_calc = cess_calc = 0.0
    grand_total_calc = 0.0
    
    for e in entries:
        amounts = e.get("amounts") or {}
        taxable = _f(amounts.get("taxable_value"))
        tax_b = amounts.get("tax_breakup") or {}
        cg = _f(tax_b.get("cgst"))
        sg = _f(tax_b.get("sgst"))
        ig = _f(tax_b.get("igst"))
        ce = _f(tax_b.get("cess"))
        total = _f(amounts.get("total"))
        
        subtotal_calc += taxable
        cgst_calc += cg
        sgst_calc += sg
        igst_calc += ig
        cess_calc += ce
        grand_total_calc += total
        
        expected_total = taxable + cg + sg + ig + ce
        if abs(total - expected_total) > tolerance:
            issues.append({
                "code": "ENTRY_TOTAL_MISMATCH",
                "level": "warning",
                "message": (
                    f"Entry {e.get('entry_id')} total {total} != taxable+tax {expected_total}"
                ),
                "meta": {"entry_id": e.get("entry_id")},
            })
    
    if abs(subtotal_canon - subtotal_calc) > tolerance:
        issues.append({
            "code": "SUBTOTAL_MISMATCH",
            "level": "warning",
            "message": f"Financials subtotal {subtotal_canon} != sum entries {subtotal_calc}",
            "meta": {},
        })
    
    taxes_calc = cgst_calc + sgst_calc + igst_calc + cess_calc
    if abs(tax_total_canon - taxes_calc) > tolerance:
        issues.append({
            "code": "TAX_TOTAL_MISMATCH",
            "level": "warning",
            "message": f"Financials tax_total {tax_total_canon} != sum entry taxes {taxes_calc}",
            "meta": {},
        })
    
    expected_grand = subtotal_canon + tax_total_canon
    if abs(grand_total_canon - expected_grand) > tolerance:
        issues.append({
            "code": "GRAND_TOTAL_MISMATCH",
            "level": "warning",
            "message": (
                f"Financials grand_total {grand_total_canon} != "
                f"subtotal+tax_total {expected_grand}"
            ),
            "meta": {},
        })
    
    return issues

