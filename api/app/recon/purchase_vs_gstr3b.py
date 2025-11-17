from __future__ import annotations

from typing import Dict, Any


def total_itc_from_purchase_register(pr: Dict[str, Any]) -> Dict[str, float]:
    entries = pr.get("entries") or []
    igst = sum((e or {}).get("igst", 0.0) or 0.0 for e in entries)
    cgst = sum((e or {}).get("cgst", 0.0) or 0.0 for e in entries)
    sgst = sum((e or {}).get("sgst", 0.0) or 0.0 for e in entries)
    return {
        "igst": round(float(igst), 2),
        "cgst": round(float(cgst), 2),
        "sgst": round(float(sgst), 2),
        "total": round(float(igst + cgst + sgst), 2),
    }


def reconcile_pr_vs_gstr3b_itc(
    pr: Dict[str, Any], g3b: Dict[str, Any], tolerance: float = 1.0
) -> Dict[str, Any]:
    pr_itc = total_itc_from_purchase_register(pr)
    g3b_itc = ((g3b or {}).get("input_tax_credit") or {}).get("total") or {}
    g3b_igst = float(g3b_itc.get("igst", 0.0) or 0.0)
    g3b_cgst = float(g3b_itc.get("cgst", 0.0) or 0.0)
    g3b_sgst = float(g3b_itc.get("sgst", 0.0) or 0.0)

    diff = {
        "igst": round(pr_itc["igst"] - g3b_igst, 2),
        "cgst": round(pr_itc["cgst"] - g3b_cgst, 2),
        "sgst": round(pr_itc["sgst"] - g3b_sgst, 2),
    }
    diff["total"] = round(diff["igst"] + diff["cgst"] + diff["sgst"], 2)

    status = "matched"
    if abs(diff["total"]) > tolerance:
        status = "itc_underclaimed" if diff["total"] < 0 else "itc_overclaimed"

    return {
        "totals": {
            "purchase_register": pr_itc,
            "gstr3b": {
                "igst": round(g3b_igst, 2),
                "cgst": round(g3b_cgst, 2),
                "sgst": round(g3b_sgst, 2),
                "total": round(g3b_igst + g3b_cgst + g3b_sgst, 2),
            },
        },
        "difference": diff,
        "status": status,
    }

