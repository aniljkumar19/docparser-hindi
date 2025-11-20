"""
GSTR-2B Validator

Validates canonical format gstr2b documents.
Returns structured validation issues with codes, levels, and metadata.
"""

from typing import Dict, Any, List


def _f(x: Any) -> float:
    """Safely convert value to float."""
    try:
        return float(x or 0.0)
    except Exception:
        return 0.0


def validate_gstr2b(doc: Dict[str, Any], tolerance: float = 1.0) -> List[Dict[str, Any]]:
    """
    Validate canonical gstr2b doc (schema_version='doc.v0.1', doc_type='gstr2b').
    
    Focus: financials vs entries (b2b subset), internal consistency.
    
    Args:
        doc: Canonical format gstr2b document
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
    
    # Aggregate from entries (b2b invoices)
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
    
    # Check that financials.tax_total equals sum tax_breakup
    taxes_from_breakup = cgst_canon + sgst_canon + igst_canon + cess_canon
    if abs(tax_total_canon - taxes_from_breakup) > tolerance:
        issues.append({
            "code": "TAX_TOTAL_MISMATCH",
            "level": "warning",
            "message": (
                f"Financials tax_total {tax_total_canon} != "
                f"sum of tax_breakup {taxes_from_breakup}"
            ),
            "meta": {},
        })
    
    # Check that grand_total = subtotal + tax_total
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
    
    # Compare entries aggregate vs canonical (but only warning, because 2B summary may include more than b2b)
    if abs(subtotal_canon - subtotal_calc) > tolerance:
        issues.append({
            "code": "SUMMARY_ENTRIES_SUBTOTAL_MISMATCH",
            "level": "warning",
            "message": (
                "GSTR-2B subtotal from summary does not match sum of B2B entries; "
                "other sections may be present (b2bur/imps/cdnr)."
            ),
            "meta": {
                "summary_subtotal": subtotal_canon,
                "b2b_subtotal": subtotal_calc,
            },
        })
    
    return issues

