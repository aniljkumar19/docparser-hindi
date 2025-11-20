"""
GSTR-2B normalizer - converts GSTR-2B documents to canonical format v0.1

GSTR-2B is an auto-drafted return showing Input Tax Credit (ITC) available
based on supplier filings (GSTR-1, GSTR-5, GSTR-6).

This normalizer creates invoice-level entries (one entry per invoice).
"""

from typing import Dict, Any, List


def _safe_float(x) -> float:
    """Safely convert value to float."""
    try:
        return float(x or 0.0)
    except Exception:
        return 0.0


def normalize_gstr2b_to_canonical(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert raw GSTR-2B JSON into canonical v0.1 format.
    
    Raw example:
    {
        "doc_type": "gstr2b",
        "gstin": "27ABCDE1234F2Z5",
        "legal_name": "ABC TRADERS PRIVATE LIMITED",
        "trade_name": "ABC TRADERS",
        "period": { "month": 11, "year": 2025, "label": "November 2025" },
        "summary": { "total_taxable_value": ..., "total_igst": ..., ... },
        "b2b": [ { "supplier_gstin": "...", "invoice_number": "...", ... } ],
        "warnings": [],
        "meta": { "parser_version": "gstr2b_v1" }
    }
    """
    
    gstin = raw.get("gstin")
    legal_name = raw.get("legal_name") or raw.get("trade_name")
    period = raw.get("period") or {}
    period_label = period.get("label")
    
    summary = raw.get("summary") or {}
    subtotal = _safe_float(summary.get("total_taxable_value"))
    total_igst = _safe_float(summary.get("total_igst"))
    total_cgst = _safe_float(summary.get("total_cgst"))
    total_sgst = _safe_float(summary.get("total_sgst"))
    total_cess = _safe_float(summary.get("total_cess"))
    tax_total = total_igst + total_cgst + total_sgst + total_cess
    
    parser_version = (raw.get("meta") or {}).get("parser_version", "gstr2b_v1")
    warnings = raw.get("warnings") or []
    
    # Build entries from b2b section
    entries: List[Dict[str, Any]] = []
    
    for idx, row in enumerate(raw.get("b2b") or [], start=1):
        if not isinstance(row, dict):
            continue
        
        taxable = _safe_float(row.get("taxable_value"))
        cgst = _safe_float(row.get("cgst"))
        sgst = _safe_float(row.get("sgst"))
        igst = _safe_float(row.get("igst"))
        cess = _safe_float(row.get("cess"))
        total = _safe_float(row.get("invoice_value")) or (taxable + cgst + sgst + igst + cess)
        
        supplier_gstin = row.get("supplier_gstin")
        supplier_name = row.get("supplier_name")
        
        entries.append({
            "entry_id": f"gstr2b-entry-{idx}",
            "entry_type": "gstr2b_invoice",
            "entry_date": row.get("invoice_date"),  # Keep as-is, already in YYYY-MM-DD format
            "entry_number": row.get("invoice_number"),
            "party": {
                "name": supplier_name,
                "gstin": supplier_gstin,
                "state_code": supplier_gstin[:2] if supplier_gstin else None,
            },
            "amounts": {
                "taxable_value": taxable,
                "tax_breakup": {
                    "cgst": cgst,
                    "sgst": sgst,
                    "igst": igst,
                    "cess": cess,
                },
                "total": total,
            },
            "line_items": [],
            "doc_specific": {
                "section": "b2b",
                "place_of_supply": row.get("place_of_supply"),
                "itc_availability": row.get("itc_availability"),
                "reason": row.get("reason"),
            },
        })
    
    canonical: Dict[str, Any] = {
        "schema_version": "doc.v0.1",
        "doc_type": "gstr2b",
        "doc_id": f"gstr2b-{period_label.lower().replace(' ', '-')}" if period_label else None,
        "doc_date": None,
        "period": period_label,
        "metadata": {
            "source_format": "gstr2b",
            "parser_version": parser_version,
            "warnings": warnings,
        },
        "business": {
            "name": legal_name,
            "gstin": gstin,
            "state_code": gstin[:2] if gstin else None,
        },
        "parties": {
            "primary": {
                "name": legal_name,
                "gstin": gstin,
                "state_code": gstin[:2] if gstin else None,
            }
        },
        "financials": {
            "currency": "INR",
            "subtotal": subtotal,
            "tax_breakup": {
                "cgst": total_cgst,
                "sgst": total_sgst,
                "igst": total_igst,
                "cess": total_cess,
            },
            "tax_total": tax_total,
            "grand_total": subtotal + tax_total,
        },
        "entries": entries,
        "doc_specific": {
            "gstr_form": "GSTR-2B",
            "legal_name": legal_name,
            "trade_name": raw.get("trade_name"),
            "summary": summary,
            "sections": {
                "b2b_count": len(raw.get("b2b") or []),
            },
        },
    }
    
    return canonical
