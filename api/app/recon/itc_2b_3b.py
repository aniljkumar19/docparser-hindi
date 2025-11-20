"""
ITC Reconciliation: GSTR-2B (available) vs GSTR-3B (claimed)

This module reconciles Input Tax Credit (ITC) between:
- GSTR-2B: Auto-drafted ITC available (from supplier filings)
- GSTR-3B: ITC claimed by taxpayer in their return

Uses canonical format (doc.v0.1) for consistent data structure.
"""

from typing import Dict, Any


def _get_tax_breakup(doc: Dict[str, Any]) -> Dict[str, float]:
    """Safely read tax_breakup from canonical.financials."""
    fin = doc.get("financials") or {}
    tb = fin.get("tax_breakup") or {}
    return {
        "igst": float(tb.get("igst") or 0.0),
        "cgst": float(tb.get("cgst") or 0.0),
        "sgst": float(tb.get("sgst") or 0.0),
        "cess": float(tb.get("cess") or 0.0),
    }


def _get_3b_itc_total(doc_3b: Dict[str, Any]) -> Dict[str, float]:
    """Read ITC total from canonical GSTR-3B doc_specific.input_tax_credit.total."""
    ds = doc_3b.get("doc_specific") or {}
    itc = (ds.get("input_tax_credit") or {}).get("total") or {}
    return {
        "igst": float(itc.get("igst") or 0.0),
        "cgst": float(itc.get("cgst") or 0.0),
        "sgst": float(itc.get("sgst") or 0.0),
        "cess": float(itc.get("cess") or 0.0),
    }


def reconcile_itc_2b_3b(
    gstr2b_doc: Dict[str, Any],
    gstr3b_doc: Dict[str, Any],
    tolerance: float = 1.0,
) -> Dict[str, Any]:
    """
    Reconcile ITC available in canonical GSTR-2B vs ITC claimed in canonical GSTR-3B.

    Args:
        gstr2b_doc: Canonical GSTR-2B document (schema_version = 'doc.v0.1')
        gstr3b_doc: Canonical GSTR-3B document (schema_version = 'doc.v0.1')
        tolerance: Tolerance for matching (default 1.0)

    Returns:
        Structured reconciliation result with:
        - gstin, period
        - itc_available_2b, itc_claimed_3b
        - by_head: breakdown by tax head (IGST, CGST, SGST, CESS)
        - overall: total comparison
        - issues: list of warnings/errors
    """
    
    # Basic identity check
    gstin_2b = (gstr2b_doc.get("business") or {}).get("gstin")
    gstin_3b = (gstr3b_doc.get("business") or {}).get("gstin")
    period_2b = gstr2b_doc.get("period")
    period_3b = gstr3b_doc.get("period")

    issues = []

    if gstin_2b != gstin_3b:
        issues.append(
            {
                "code": "GSTIN_MISMATCH",
                "level": "error",
                "message": f"GSTIN mismatch: 2B={gstin_2b}, 3B={gstin_3b}",
            }
        )

    if period_2b != period_3b:
        issues.append(
            {
                "code": "PERIOD_MISMATCH",
                "level": "error",
                "message": f"Period mismatch: 2B='{period_2b}', 3B='{period_3b}'",
            }
        )

    # ITC from 2B (available)
    itc_2b = _get_tax_breakup(gstr2b_doc)
    total_2b = sum(itc_2b.values())

    # ITC from 3B (claimed)
    itc_3b = _get_3b_itc_total(gstr3b_doc)
    total_3b = sum(itc_3b.values())

    # Head-wise diffs
    heads = ["igst", "cgst", "sgst", "cess"]
    head_results = {}
    for h in heads:
        available = itc_2b.get(h, 0.0)
        claimed = itc_3b.get(h, 0.0)
        diff = claimed - available
        status = "match"
        if abs(diff) > tolerance:
            status = "over_claimed" if diff > 0 else "under_claimed"

        head_results[h] = {
            "available_2b": available,
            "claimed_3b": claimed,
            "difference": diff,
            "status": status,
        }

        if status != "match":
            issues.append(
                {
                    "code": f"ITC_{h.upper()}_MISMATCH",
                    "level": "warning",
                    "message": (
                        f"{h.upper()} ITC mismatch: available in 2B={available}, "
                        f"claimed in 3B={claimed}, diff={diff}"
                    ),
                }
            )

    overall_diff = total_3b - total_2b
    overall_status = "match"
    if abs(overall_diff) > tolerance:
        overall_status = "over_claimed" if overall_diff > 0 else "under_claimed"

    result = {
        "gstin": gstin_2b or gstin_3b,
        "period": period_2b or period_3b,
        "itc_available_2b": itc_2b,
        "itc_claimed_3b": itc_3b,
        "by_head": head_results,
        "overall": {
            "total_available_2b": total_2b,
            "total_claimed_3b": total_3b,
            "difference": overall_diff,
            "status": overall_status,
        },
        "issues": issues,
    }

    return result

