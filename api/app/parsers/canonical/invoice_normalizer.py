"""
Invoice normalizer - converts invoice documents to canonical format v0.1
"""

from typing import Dict, Any
from .base import (
    _extract_value,
    _extract_address,
    _extract_state_code,
    _normalize_date,
    _to_float,
    _build_tax_breakup_from_taxes,
    _generate_doc_id,
)


def normalize_invoice_to_canonical(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Convert invoice to canonical format."""
    
    # Extract common fields
    invoice_number = _extract_value(parsed.get("invoice_number"))
    invoice_date = _extract_value(parsed.get("date")) or _extract_value(parsed.get("invoice_date"))
    
    # Extract seller/buyer
    seller = parsed.get("seller") or {}
    buyer = parsed.get("buyer") or {}
    
    # Extract financials
    totals = parsed.get("totals") or {}
    tax_breakup = parsed.get("tax_breakup") or {}
    
    # If tax_breakup is empty, try to build from taxes array
    if not tax_breakup and parsed.get("taxes"):
        tax_breakup = _build_tax_breakup_from_taxes(parsed.get("taxes", []))
    
    # If still empty, try to extract from flat fields
    if not tax_breakup:
        tax_breakup = {
            "cgst": float(parsed.get("cgst", 0) or 0),
            "sgst": float(parsed.get("sgst", 0) or 0),
            "igst": float(parsed.get("igst", 0) or 0),
            "cess": float(parsed.get("cess", 0) or 0),
        }
    
    # Extract line items
    items = parsed.get("items") or parsed.get("line_items") or []
    line_items = []
    for item in items:
        line_items.append({
            "description": item.get("description") or item.get("desc") or "",
            "hsn_sac": item.get("hsn_sac") or item.get("hsn") or None,
            "quantity": _to_float(item.get("quantity") or item.get("qty")),
            "unit": item.get("unit") or None,
            "unit_price": _to_float(item.get("unit_price") or item.get("rate")),
            "amount": _to_float(item.get("amount")),
            "tax_rate": _to_float(item.get("tax_rate")),
            "tax_amount": _to_float(item.get("tax_amount")),
        })
    
    # Build canonical structure
    canonical = {
        "schema_version": "doc.v0.1",
        "doc_type": parsed.get("doc_type") or "invoice",
        "doc_id": _generate_doc_id("invoice", invoice_number),
        "doc_date": _normalize_date(invoice_date),
        "period": None,
        
        "metadata": {
            "source_format": "invoice",
            "parser_version": parsed.get("meta", {}).get("parser_version", "unknown"),
            "warnings": parsed.get("warnings", []),
        },
        
        "business": {
            "name": _extract_value(seller.get("name")) if isinstance(seller, dict) else None,
            "gstin": _extract_value(seller.get("gstin")) if isinstance(seller, dict) else None,
            "address": _extract_address(seller) if isinstance(seller, dict) else {},
            "state_code": _extract_state_code(_extract_value(seller.get("gstin")) if isinstance(seller, dict) else None),
        },
        
        "parties": {
            "primary": {
                "name": _extract_value(seller.get("name")) if isinstance(seller, dict) else None,
                "gstin": _extract_value(seller.get("gstin")) if isinstance(seller, dict) else None,
                "address": _extract_address(seller) if isinstance(seller, dict) else {},
                "state_code": _extract_state_code(_extract_value(seller.get("gstin")) if isinstance(seller, dict) else None),
            },
            "counterparty": {
                "name": _extract_value(buyer.get("name")) if isinstance(buyer, dict) else None,
                "gstin": _extract_value(buyer.get("gstin")) if isinstance(buyer, dict) else None,
                "address": _extract_address(buyer) if isinstance(buyer, dict) else {},
                "state_code": _extract_state_code(_extract_value(buyer.get("gstin")) if isinstance(buyer, dict) else None),
            },
        },
        
        "financials": {
            "currency": totals.get("currency") or parsed.get("currency") or "INR",
            "subtotal": _to_float(totals.get("subtotal") or parsed.get("subtotal")),
            "tax_breakup": {
                "cgst": _to_float(tax_breakup.get("cgst", 0)),
                "sgst": _to_float(tax_breakup.get("sgst", 0)),
                "igst": _to_float(tax_breakup.get("igst", 0)),
                "cess": _to_float(tax_breakup.get("cess", 0)),
                "tds": _to_float(tax_breakup.get("tds", 0)),
                "tcs": _to_float(tax_breakup.get("tcs", 0)),
            },
            "tax_total": _to_float(totals.get("tax_total") or tax_breakup.get("cgst", 0) + tax_breakup.get("sgst", 0) + tax_breakup.get("igst", 0) + tax_breakup.get("cess", 0)),
            "grand_total": _to_float(totals.get("grand_total") or parsed.get("total")),
            "round_off": _to_float(totals.get("round_off", 0)),
        },
        
        "entries": [
            {
                "entry_id": "main-invoice",
                "entry_type": "invoice",
                "entry_date": _normalize_date(invoice_date),
                "entry_number": invoice_number,
                "line_items": line_items,
                "amounts": {
                    "taxable_value": _to_float(totals.get("subtotal") or parsed.get("subtotal")),
                    "tax_breakup": {
                        "cgst": _to_float(tax_breakup.get("cgst", 0)),
                        "sgst": _to_float(tax_breakup.get("sgst", 0)),
                        "igst": _to_float(tax_breakup.get("igst", 0)),
                        "cess": _to_float(tax_breakup.get("cess", 0)),
                    },
                    "total": _to_float(totals.get("grand_total") or parsed.get("total")),
                },
                "doc_specific": {},
            }
        ],
        
        "doc_specific": {
            "due_date": _normalize_date(parsed.get("due_date")),
            "po_number": parsed.get("po_number"),
            "place_of_supply": parsed.get("place_of_supply"),
            "notes": parsed.get("notes"),
        },
    }
    
    return canonical

