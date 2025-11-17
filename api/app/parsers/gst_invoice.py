from __future__ import annotations

import re
from typing import Any, Dict, List

from .rules import parse_text_rules as parse_generic_invoice, GSTIN_REGEX

INVOICE_NO_GARBAGE = re.compile(r"^[A-Za-z]{1,3}$")
INVOICE_ALLOW = re.compile(r"^[A-Za-z0-9\-\/]+$")
INVOICE_REGEX = re.compile(r"(?:invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)", re.IGNORECASE)


def _clean_invoice_number(value: str | None) -> str | None:
    if not value:
        return None
    token = value.strip()
    if not token or len(token) < 4:
        return None
    if INVOICE_NO_GARBAGE.match(token):
        return None
    token = token.replace(" ", "")
    if not INVOICE_ALLOW.match(token):
        token = re.sub(r"[^A-Za-z0-9\-\/]", "", token)
    return token or None


def _clean_invoice_list(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    seen = set()
    for entry in entries or []:
        num = entry.get("invoice_number")
        cleaned_num = _clean_invoice_number(num)
        if not cleaned_num:
            continue
        if cleaned_num in seen:
            continue
        seen.add(cleaned_num)
        cleaned.append({"invoice_number": cleaned_num})
    return cleaned


def parse_text_rules(text: str) -> Dict[str, Any]:
    parsed = parse_generic_invoice(text)
    parsed["doc_type"] = "gst_invoice"
    parsed.setdefault("warnings", [])

    invoice_field = parsed.get("invoice_number")
    if isinstance(invoice_field, dict):
        cleaned_value = _clean_invoice_number(invoice_field.get("value"))
        if cleaned_value:
            invoice_field["value"] = cleaned_value
    else:
        match = INVOICE_REGEX.search(text)
        if match:
            parsed["invoice_number"] = {"value": match.group(1).strip(), "confidence": 0.8}

    matches = GSTIN_REGEX.findall(text)
    if matches:
        seller = parsed.get("seller") or {}
        parsed["seller"] = seller
        seller.setdefault("gstin", matches[0])
        if len(matches) > 1:
            buyer = parsed.get("buyer") or {}
            parsed["buyer"] = buyer
            buyer.setdefault("gstin", matches[1])
    else:
        parsed["warnings"].append("GSTIN not found")

    parsed["invoices"] = _clean_invoice_list(parsed.get("invoices", []))
    return parsed

