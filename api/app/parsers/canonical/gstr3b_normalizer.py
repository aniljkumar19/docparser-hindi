"""
GSTR-3B normalizer - converts GSTR-3B documents to canonical format v0.1
"""

from typing import Dict, Any
from .base import (
    _extract_value,
    _extract_state_code,
    _normalize_date,
    _to_float,
    _generate_doc_id,
)


def normalize_gstr3b_to_canonical(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Convert GSTR-3B to canonical format (matching sales_register style)."""
    
    # Extract period - handle both string and object formats
    period_obj = parsed.get("period")
    if isinstance(period_obj, dict):
        period_label = period_obj.get("label")
        period_month = period_obj.get("month")
        period_year = period_obj.get("year")
        if period_label:
            period = period_label
        elif period_month and period_year:
            # Format as YYYY-MM
            period = f"{period_year}-{period_month:02d}"
        else:
            period = None
    else:
        period = _extract_value(period_obj)
    
    # Extract business info
    gstin = parsed.get("gstin") or _extract_value(parsed.get("gstin"))
    legal_name = parsed.get("legal_name")
    trade_name = parsed.get("trade_name")
    business_name = legal_name or trade_name or _extract_value(parsed.get("business_name"))
    
    # Extract outward supplies (main taxable supplies)
    outward = parsed.get("outward_supplies", {})
    outward_taxable = _to_float(outward.get("taxable_value", 0))
    outward_cgst = _to_float(outward.get("cgst", 0))
    outward_sgst = _to_float(outward.get("sgst", 0))
    outward_igst = _to_float(outward.get("igst", 0))
    outward_cess = _to_float(outward.get("cess", 0))
    
    # Extract reverse charge inward supplies
    rc_inward = parsed.get("reverse_charge_inward_supplies", {})
    rc_taxable = _to_float(rc_inward.get("taxable_value", 0))
    rc_cgst = _to_float(rc_inward.get("cgst", 0))
    rc_sgst = _to_float(rc_inward.get("sgst", 0))
    rc_igst = _to_float(rc_inward.get("igst", 0))
    rc_cess = _to_float(rc_inward.get("cess", 0))
    
    # Extract ITC (Input Tax Credit)
    itc = parsed.get("input_tax_credit", {})
    itc_total = itc.get("total", {})
    
    # Extract tax payable and tax paid
    tax_payable = parsed.get("tax_payable", {})
    tax_paid = parsed.get("tax_paid", {})
    
    # Calculate aggregated totals
    total_taxable = outward_taxable + rc_taxable
    total_cgst = outward_cgst + rc_cgst
    total_sgst = outward_sgst + rc_sgst
    total_igst = outward_igst + rc_igst
    total_cess = outward_cess + rc_cess
    total_tax = total_cgst + total_sgst + total_igst + total_cess
    
    # Build entries - GSTR-3B has summary entries, not individual invoices
    canonical_entries = []
    
    # Entry 1: Outward taxable supplies
    if outward_taxable > 0 or total_cgst > 0 or total_sgst > 0 or total_igst > 0:
        canonical_entries.append({
            "entry_id": "gstr3b-outward-supplies",
            "entry_type": "gstr_entry",
            "entry_date": None,  # GSTR-3B is period-based, not date-based
            "entry_number": "OUTWARD",
            "party": None,  # GSTR-3B is business-level, not party-specific
            "amounts": {
                "taxable_value": outward_taxable,
                "tax_breakup": {
                    "cgst": outward_cgst,
                    "sgst": outward_sgst,
                    "igst": outward_igst,
                    "cess": outward_cess,
                },
                "total": outward_taxable + outward_cgst + outward_sgst + outward_igst + outward_cess,
            },
            "line_items": [],
            "doc_specific": {
                "supply_type": "outward_taxable",
            },
        })
    
    # Entry 2: Reverse charge inward supplies
    if rc_taxable > 0 or rc_cgst > 0 or rc_sgst > 0 or rc_igst > 0:
        canonical_entries.append({
            "entry_id": "gstr3b-reverse-charge",
            "entry_type": "gstr_entry",
            "entry_date": None,
            "entry_number": "REVERSE_CHARGE",
            "party": None,
            "amounts": {
                "taxable_value": rc_taxable,
                "tax_breakup": {
                    "cgst": rc_cgst,
                    "sgst": rc_sgst,
                    "igst": rc_igst,
                    "cess": rc_cess,
                },
                "total": rc_taxable + rc_cgst + rc_sgst + rc_igst + rc_cess,
            },
            "line_items": [],
            "doc_specific": {
                "supply_type": "reverse_charge_inward",
            },
        })
    
    # If no structured entries, try to extract from invoices array (fallback)
    if not canonical_entries:
        invoices = parsed.get("invoices", [])
        for idx, inv in enumerate(invoices):
            canonical_entries.append({
                "entry_id": f"gstr-entry-{idx + 1}",
                "entry_type": "gstr_entry",
                "entry_date": _normalize_date(inv.get("date")),
                "entry_number": inv.get("invoice_number"),
                "amounts": {
                    "taxable_value": _to_float(inv.get("value")),
                    "tax_breakup": {},
                    "total": _to_float(inv.get("value")),
                },
                "line_items": [],
                "doc_specific": {},
            })
    
    canonical = {
        "schema_version": "doc.v0.1",
        "doc_type": "gstr3b",
        "doc_id": _generate_doc_id("gstr3b", period),
        "doc_date": None,
        "period": period,
        
        "metadata": {
            "source_format": "gstr3b",
            "parser_version": parsed.get("meta", {}).get("parser_version", "unknown"),
            "warnings": parsed.get("warnings", []),
        },
        
        "business": {
            "name": business_name,
            "gstin": gstin,
            "state_code": _extract_state_code(gstin),
        },
        
        "parties": {
            "primary": {
                "name": business_name,
                "gstin": gstin,
                "state_code": _extract_state_code(gstin),
            },
        },
        
        "financials": {
            "currency": "INR",
            "subtotal": total_taxable,
            "tax_breakup": {
                "cgst": total_cgst,
                "sgst": total_sgst,
                "igst": total_igst,
                "cess": total_cess,
            },
            "tax_total": total_tax,
            "grand_total": total_taxable + total_tax,
        },
        
        "entries": canonical_entries,
        
        "doc_specific": {
            "gstr_form": "GSTR-3B",
            "legal_name": legal_name,
            "trade_name": trade_name,
            "outward_supplies": {
                "taxable_value": outward_taxable,
                "cgst": outward_cgst,
                "sgst": outward_sgst,
                "igst": outward_igst,
                "cess": outward_cess,
            },
            "reverse_charge_inward_supplies": {
                "taxable_value": rc_taxable,
                "cgst": rc_cgst,
                "sgst": rc_sgst,
                "igst": rc_igst,
                "cess": rc_cess,
            },
            "input_tax_credit": {
                "total": {
                    "igst": _to_float(itc_total.get("igst", 0)),
                    "cgst": _to_float(itc_total.get("cgst", 0)),
                    "sgst": _to_float(itc_total.get("sgst", 0)),
                    "cess": _to_float(itc_total.get("cess", 0)),
                },
            },
            "tax_payable": {
                "igst": _to_float(tax_payable.get("igst", 0)),
                "cgst": _to_float(tax_payable.get("cgst", 0)),
                "sgst": _to_float(tax_payable.get("sgst", 0)),
                "cess": _to_float(tax_payable.get("cess", 0)),
            },
            "tax_paid": {
                "through_itc": {
                    "igst": _to_float(tax_paid.get("through_itc", {}).get("igst", 0)),
                    "cgst": _to_float(tax_paid.get("through_itc", {}).get("cgst", 0)),
                    "sgst": _to_float(tax_paid.get("through_itc", {}).get("sgst", 0)),
                    "cess": _to_float(tax_paid.get("through_itc", {}).get("cess", 0)),
                },
                "in_cash": {
                    "igst": _to_float(tax_paid.get("in_cash", {}).get("igst", 0)),
                    "cgst": _to_float(tax_paid.get("in_cash", {}).get("cgst", 0)),
                    "sgst": _to_float(tax_paid.get("in_cash", {}).get("sgst", 0)),
                    "cess": _to_float(tax_paid.get("in_cash", {}).get("cess", 0)),
                },
            },
            "exempt_nil_nongst_supplies": parsed.get("exempt_nil_nongst_supplies", {}),
            "verification": parsed.get("verification", {}),
        },
    }
    
    return canonical

