"""
Sales Register Validator

Validates canonical format sales_register documents.
Returns structured validation issues with codes, levels, and metadata.
"""

from typing import Dict, Any, List


def _f(x: Any) -> float:
    """Safely convert value to float."""
    try:
        return float(x or 0.0)
    except Exception:
        return 0.0


def validate_sales_register(doc: Dict[str, Any], tolerance: float = 1.0) -> List[Dict[str, Any]]:
    """
    Validate canonical sales_register doc.
    
    Args:
        doc: Canonical format sales_register document
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
    
    # Extract totals from financials section
    subtotal_canonical = _f(financials.get("subtotal"))
    tax_breakup = financials.get("tax_breakup") or {}
    cgst_total_canon = _f(tax_breakup.get("cgst"))
    sgst_total_canon = _f(tax_breakup.get("sgst"))
    igst_total_canon = _f(tax_breakup.get("igst"))
    cess_total_canon = _f(tax_breakup.get("cess"))
    tax_total_canon = _f(financials.get("tax_total"))
    grand_total_canon = _f(financials.get("grand_total"))
    
    # Aggregate from entries
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
        
        # Per-entry check: total ≈ taxable + taxes
        expected_total = taxable + cg + sg + ig + ce
        if abs(total - expected_total) > tolerance:
            issues.append({
                "code": "ENTRY_TOTAL_MISMATCH",
                "level": "warning",
                "message": f"Entry {e.get('entry_id')} total {total} != taxable+tax {expected_total}",
                "meta": {"entry_id": e.get("entry_id")},
            })
    
    # Global checks: financials totals vs sum of entries
    
    if abs(subtotal_canonical - subtotal_calc) > tolerance:
        issues.append({
            "code": "SUBTOTAL_MISMATCH",
            "level": "warning",
            "message": f"Financials subtotal {subtotal_canonical} != sum entries {subtotal_calc}",
            "meta": {},
        })
    
    if abs(cgst_total_canon - cgst_calc) > tolerance:
        issues.append({
            "code": "CGST_TOTAL_MISMATCH",
            "level": "warning",
            "message": f"Financials CGST {cgst_total_canon} != sum entries {cgst_calc}",
            "meta": {},
        })
    
    if abs(sgst_total_canon - sgst_calc) > tolerance:
        issues.append({
            "code": "SGST_TOTAL_MISMATCH",
            "level": "warning",
            "message": f"Financials SGST {sgst_total_canon} != sum entries {sgst_calc}",
            "meta": {},
        })
    
    if abs(igst_total_canon - igst_calc) > tolerance:
        issues.append({
            "code": "IGST_TOTAL_MISMATCH",
            "level": "warning",
            "message": f"Financials IGST {igst_total_canon} != sum entries {igst_calc}",
            "meta": {},
        })
    
    if abs(cess_total_canon - cess_calc) > tolerance:
        issues.append({
            "code": "CESS_TOTAL_MISMATCH",
            "level": "warning",
            "message": f"Financials CESS {cess_total_canon} != sum entries {cess_calc}",
            "meta": {},
        })
    
    taxes_calc = cgst_calc + sgst_calc + igst_calc + cess_calc
    if abs(tax_total_canon - taxes_calc) > tolerance:
        issues.append({
            "code": "TAX_TOTAL_MISMATCH",
            "level": "warning",
            "message": f"Financials tax_total {tax_total_canon} != sum taxes {taxes_calc}",
            "meta": {},
        })
    
    expected_grand_total = subtotal_canonical + tax_total_canon
    if abs(grand_total_canon - expected_grand_total) > tolerance:
        issues.append({
            "code": "GRAND_TOTAL_MISMATCH",
            "level": "warning",
            "message": f"Financials grand_total {grand_total_canon} != subtotal+tax_total {expected_grand_total}",
            "meta": {},
        })
    
    return issues
