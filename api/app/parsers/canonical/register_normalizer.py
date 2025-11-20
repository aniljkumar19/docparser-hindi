"""
Register normalizers - converts purchase and sales register documents to canonical format v0.1
"""

from typing import Dict, Any
from .base import (
    _extract_value,
    _extract_state_code,
    _normalize_date,
    _to_float,
    _generate_doc_id,
)


def normalize_purchase_register_to_canonical(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Convert purchase register to canonical format."""
    
    entries_data = parsed.get("entries", [])
    period = parsed.get("period")
    gstin_of_business = parsed.get("gstin_of_business")
    
    # Calculate totals
    total_subtotal = sum(_to_float(e.get("taxable_value", 0)) for e in entries_data)
    total_cgst = sum(_to_float(e.get("cgst", 0)) for e in entries_data)
    total_sgst = sum(_to_float(e.get("sgst", 0)) for e in entries_data)
    total_igst = sum(_to_float(e.get("igst", 0)) for e in entries_data)
    total_cess = sum(_to_float(e.get("cess", 0)) for e in entries_data)
    total_grand = sum(_to_float(e.get("total_value", 0)) for e in entries_data)
    
    # Build entries
    canonical_entries = []
    for idx, entry in enumerate(entries_data):
        canonical_entries.append({
            "entry_id": f"entry-{idx + 1}",
            "entry_type": "register_entry",
            "entry_date": _normalize_date(entry.get("invoice_date")),
            "entry_number": entry.get("invoice_number"),
            "party": {
                "name": entry.get("supplier_name"),
                "gstin": entry.get("supplier_gstin"),
                "state_code": _extract_state_code(entry.get("supplier_gstin")),
            },
            "amounts": {
                "taxable_value": _to_float(entry.get("taxable_value", 0)),
                "tax_breakup": {
                    "cgst": _to_float(entry.get("cgst", 0)),
                    "sgst": _to_float(entry.get("sgst", 0)),
                    "igst": _to_float(entry.get("igst", 0)),
                    "cess": _to_float(entry.get("cess", 0)),
                },
                "total": _to_float(entry.get("total_value", 0)),
            },
            "line_items": [],  # Purchase registers typically don't have line items
            "doc_specific": {
                "reverse_charge": entry.get("reverse_charge", False),
                "invoice_type": entry.get("invoice_type", "REGULAR"),
                "place_of_supply": entry.get("place_of_supply"),
                "hsn_summary": entry.get("hsn_summary", []),
            },
        })
    
    canonical = {
        "schema_version": "doc.v0.1",
        "doc_type": "purchase_register",
        "doc_id": _generate_doc_id("purchase_register", period),
        "doc_date": None,
        "period": period,
        
        "metadata": {
            "source_format": "purchase_register",
            "parser_version": parsed.get("meta", {}).get("parser_version", "unknown"),
            "warnings": parsed.get("warnings", []),
        },
        
        "business": {
            "name": None,
            "gstin": gstin_of_business,
            "state_code": _extract_state_code(gstin_of_business),
        },
        
        "parties": {
            "primary": {
                "name": None,
                "gstin": gstin_of_business,
                "state_code": _extract_state_code(gstin_of_business),
            },
        },
        
        "financials": {
            "currency": "INR",
            "subtotal": total_subtotal,
            "tax_breakup": {
                "cgst": total_cgst,
                "sgst": total_sgst,
                "igst": total_igst,
                "cess": total_cess,
            },
            "tax_total": total_cgst + total_sgst + total_igst + total_cess,
            "grand_total": total_grand,
        },
        
        "entries": canonical_entries,
        
        "doc_specific": {
            "total_invoices": len(entries_data),
            "total_suppliers": len(set(e.get("supplier_name") for e in entries_data if e.get("supplier_name"))),
        },
    }
    
    return canonical


def normalize_sales_register_to_canonical(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Convert sales register to canonical format."""
    
    entries_data = parsed.get("entries", [])
    period = parsed.get("period")
    gstin_of_business = parsed.get("gstin_of_business")
    
    # Calculate totals
    total_subtotal = sum(_to_float(e.get("taxable_value", 0)) for e in entries_data)
    total_cgst = sum(_to_float(e.get("cgst", 0)) for e in entries_data)
    total_sgst = sum(_to_float(e.get("sgst", 0)) for e in entries_data)
    total_igst = sum(_to_float(e.get("igst", 0)) for e in entries_data)
    total_cess = sum(_to_float(e.get("cess", 0)) for e in entries_data)
    total_grand = sum(_to_float(e.get("total_value", 0)) for e in entries_data)
    
    # Build entries
    canonical_entries = []
    for idx, entry in enumerate(entries_data):
        canonical_entries.append({
            "entry_id": f"entry-{idx + 1}",
            "entry_type": "register_entry",
            "entry_date": _normalize_date(entry.get("invoice_date")),
            "entry_number": entry.get("invoice_number"),
            "party": {
                "name": entry.get("customer_name"),
                "gstin": entry.get("customer_gstin"),
                "state_code": _extract_state_code(entry.get("customer_gstin")),
            },
            "amounts": {
                "taxable_value": _to_float(entry.get("taxable_value", 0)),
                "tax_breakup": {
                    "cgst": _to_float(entry.get("cgst", 0)),
                    "sgst": _to_float(entry.get("sgst", 0)),
                    "igst": _to_float(entry.get("igst", 0)),
                    "cess": _to_float(entry.get("cess", 0)),
                },
                "total": _to_float(entry.get("total_value", 0)),
            },
            "line_items": [],
            "doc_specific": {
                "reverse_charge": entry.get("reverse_charge", False),
                "invoice_type": entry.get("invoice_type", "REGULAR"),
                "place_of_supply": entry.get("place_of_supply"),
                "hsn_summary": entry.get("hsn_summary", []),
            },
        })
    
    canonical = {
        "schema_version": "doc.v0.1",
        "doc_type": "sales_register",
        "doc_id": _generate_doc_id("sales_register", period),
        "doc_date": None,
        "period": period,
        
        "metadata": {
            "source_format": "sales_register",
            "parser_version": parsed.get("meta", {}).get("parser_version", "unknown"),
            "warnings": parsed.get("warnings", []),
        },
        
        "business": {
            "name": None,
            "gstin": gstin_of_business,
            "state_code": _extract_state_code(gstin_of_business),
        },
        
        "parties": {
            "primary": {
                "name": None,
                "gstin": gstin_of_business,
                "state_code": _extract_state_code(gstin_of_business),
            },
        },
        
        "financials": {
            "currency": "INR",
            "subtotal": total_subtotal,
            "tax_breakup": {
                "cgst": total_cgst,
                "sgst": total_sgst,
                "igst": total_igst,
                "cess": total_cess,
            },
            "tax_total": total_cgst + total_sgst + total_igst + total_cess,
            "grand_total": total_grand,
        },
        
        "entries": canonical_entries,
        
        "doc_specific": {
            "total_invoices": len(entries_data),
            "total_customers": len(set(e.get("customer_name") for e in entries_data if e.get("customer_name"))),
        },
    }
    
    return canonical

