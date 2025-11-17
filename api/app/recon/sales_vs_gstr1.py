from __future__ import annotations

from typing import Any, Dict, List


def total_from_sales_register(sr: Dict[str, Any]) -> Dict[str, float]:
    entries = sr.get("entries") or []
    taxable = 0.0
    igst = 0.0
    cgst = 0.0
    sgst = 0.0
    total_val = 0.0
    for e in entries:
        if not isinstance(e, dict):
            continue
        taxable += float(e.get("taxable_value") or 0.0)
        igst += float(e.get("igst") or 0.0)
        cgst += float(e.get("cgst") or 0.0)
        sgst += float(e.get("sgst") or 0.0)
        total_val += float(e.get("total_value") or 0.0)
    return {
        "taxable_value": round(taxable, 2),
        "igst": round(igst, 2),
        "cgst": round(cgst, 2),
        "sgst": round(sgst, 2),
        "total": round(total_val, 2),
    }


def total_from_gstr1(g1: Dict[str, Any]) -> Dict[str, float]:
    invoices: List[Dict[str, Any]] = g1.get("b2b_invoices") or []
    taxable = 0.0
    igst = 0.0
    cgst = 0.0
    sgst = 0.0
    total_val = 0.0
    for inv in invoices:
        if not isinstance(inv, dict):
            continue
        taxable += float(inv.get("taxable_value") or 0.0)
        igst += float(inv.get("igst") or 0.0)
        cgst += float(inv.get("cgst") or 0.0)
        sgst += float(inv.get("sgst") or 0.0)
        # GSTR-1 dummy doesn't carry per-invoice total, so reconstruct
        total_val += float(inv.get("taxable_value") or 0.0) + float(
            (inv.get("igst") or 0.0)
        ) + float(inv.get("cgst") or 0.0) + float(inv.get("sgst") or 0.0) + float(
            inv.get("cess") or 0.0
        )
    return {
        "taxable_value": round(taxable, 2),
        "igst": round(igst, 2),
        "cgst": round(cgst, 2),
        "sgst": round(sgst, 2),
        "total": round(total_val, 2),
    }


def reconcile_sales_register_vs_gstr1(
    sr: Dict[str, Any], g1: Dict[str, Any], tolerance: float = 1.0
) -> Dict[str, Any]:
    sr_totals = total_from_sales_register(sr)
    g1_totals = total_from_gstr1(g1)

    diff = {
        "taxable_value": round(
            sr_totals["taxable_value"] - g1_totals["taxable_value"], 2
        ),
        "igst": round(sr_totals["igst"] - g1_totals["igst"], 2),
        "cgst": round(sr_totals["cgst"] - g1_totals["cgst"], 2),
        "sgst": round(sr_totals["sgst"] - g1_totals["sgst"], 2),
        "total": round(sr_totals["total"] - g1_totals["total"], 2),
    }

    status = "matched"
    if abs(diff["total"]) > tolerance:
        # sales register > GSTR-1 => turnover under-reported in return
        status = (
            "turnover_underreported" if diff["total"] > 0 else "turnover_overreported"
        )

    return {
        "status": status,
        "totals": {
            "sales_register": sr_totals,
            "gstr1": g1_totals,
        },
        "difference": diff,
        "warnings": [],
    }


