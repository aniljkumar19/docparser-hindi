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


def _normalize_invoice_number(inv_no: str | None) -> str | None:
    """Normalize invoice number for matching (strip, uppercase, remove spaces/dashes)"""
    if not inv_no:
        return None
    if isinstance(inv_no, dict):
        inv_no = inv_no.get("value") or inv_no.get("invoice_number")
    if not isinstance(inv_no, str):
        return None
    return inv_no.strip().upper().replace(" ", "").replace("-", "").replace("_", "")


def _get_invoice_key(entry: Dict[str, Any]) -> str | None:
    """Generate a unique key for an invoice (invoice_number + optional date)"""
    inv_no = entry.get("invoice_number")
    if isinstance(inv_no, dict):
        inv_no = inv_no.get("value")
    inv_no_norm = _normalize_invoice_number(inv_no)
    if not inv_no_norm:
        return None
    
    # Optionally include date for better matching
    inv_date = entry.get("invoice_date") or entry.get("date")
    if isinstance(inv_date, dict):
        inv_date = inv_date.get("value")
    if inv_date:
        return f"{inv_no_norm}|{inv_date}"
    return inv_no_norm


def _calculate_invoice_total(entry: Dict[str, Any]) -> float:
    """Calculate total invoice value from entry"""
    taxable = float(entry.get("taxable_value") or 0.0)
    igst = float(entry.get("igst") or 0.0)
    cgst = float(entry.get("cgst") or 0.0)
    sgst = float(entry.get("sgst") or 0.0)
    cess = float(entry.get("cess") or 0.0)
    total_val = float(entry.get("total_value") or 0.0)
    
    # If total_value is not provided, calculate it
    if total_val == 0.0:
        total_val = taxable + igst + cgst + sgst + cess
    
    return round(total_val, 2)


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

    # Build invoice-level reconciliation
    sr_entries = sr.get("entries") or []
    g1_invoices = g1.get("b2b_invoices") or []
    
    # Create lookup maps
    sr_map: Dict[str, Dict[str, Any]] = {}
    for entry in sr_entries:
        if not isinstance(entry, dict):
            continue
        key = _get_invoice_key(entry)
        if key:
            sr_map[key] = entry
    
    g1_map: Dict[str, Dict[str, Any]] = {}
    for inv in g1_invoices:
        if not isinstance(inv, dict):
            continue
        key = _get_invoice_key(inv)
        if key:
            g1_map[key] = inv
    
    # Find missing invoices
    missing_in_gstr1: List[Dict[str, Any]] = []
    missing_in_sales_register: List[Dict[str, Any]] = []
    value_mismatches: List[Dict[str, Any]] = []
    
    # Check sales register entries
    for key, sr_entry in sr_map.items():
        g1_entry = g1_map.get(key)
        if not g1_entry:
            # Invoice in sales register but not in GSTR-1
            missing_in_gstr1.append({
                "invoice_number": sr_entry.get("invoice_number"),
                "invoice_date": sr_entry.get("invoice_date") or sr_entry.get("date"),
                "taxable_value": sr_entry.get("taxable_value"),
                "total_value": _calculate_invoice_total(sr_entry),
            })
        else:
            # Check for value mismatches
            sr_total = _calculate_invoice_total(sr_entry)
            g1_total = _calculate_invoice_total(g1_entry)
            
            sr_taxable = float(sr_entry.get("taxable_value") or 0.0)
            g1_taxable = float(g1_entry.get("taxable_value") or 0.0)
            
            if abs(sr_total - g1_total) > tolerance or abs(sr_taxable - g1_taxable) > tolerance:
                # Flatten structure to match dashboard expectations
                value_mismatches.append({
                    "invoice_number": sr_entry.get("invoice_number"),
                    "invoice_date": sr_entry.get("invoice_date") or sr_entry.get("date"),
                    "sales_register_value": sr_total,
                    "gstr1_value": g1_total,
                    "difference": round(sr_total - g1_total, 2),
                    # Also include detailed breakdown for future use
                    "sales_register": {
                        "taxable_value": sr_taxable,
                        "igst": float(sr_entry.get("igst") or 0.0),
                        "cgst": float(sr_entry.get("cgst") or 0.0),
                        "sgst": float(sr_entry.get("sgst") or 0.0),
                        "total": sr_total,
                    },
                    "gstr1": {
                        "taxable_value": g1_taxable,
                        "igst": float(g1_entry.get("igst") or 0.0),
                        "cgst": float(g1_entry.get("cgst") or 0.0),
                        "sgst": float(g1_entry.get("sgst") or 0.0),
                        "total": g1_total,
                    },
                })
    
    # Check GSTR-1 invoices
    for key, g1_entry in g1_map.items():
        if key not in sr_map:
            # Invoice in GSTR-1 but not in sales register
            missing_in_sales_register.append({
                "invoice_number": g1_entry.get("invoice_number"),
                "invoice_date": g1_entry.get("invoice_date") or g1_entry.get("date"),
                "taxable_value": g1_entry.get("taxable_value"),
                "total": _calculate_invoice_total(g1_entry),
            })

    return {
        "status": status,
        "totals": {
            "sales_register": sr_totals,
            "gstr1": g1_totals,
        },
        "difference": diff,
        "missing_in_gstr1": missing_in_gstr1,
        "missing_in_sales_register": missing_in_sales_register,
        "value_mismatches": value_mismatches,
        "warnings": [],
    }


