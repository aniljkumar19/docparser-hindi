from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .rules import normalize_date as _normalize_date

INVOICE_NO_RE = re.compile(
    r"(?:invoice|tax\s+invoice)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-\/]+)",
    re.IGNORECASE,
)
BILL_DATE_RE = re.compile(
    r"bill\s+date\s+([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})",
    re.IGNORECASE,
)
SUBTOTAL_RE = re.compile(
    r"sub\s*total\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)
TOTAL_RE = re.compile(
    r"(?:grand\s+total|total\s+rs\.?|total)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)
TAX_LINE_RE = re.compile(
    r"(cgst|sgst|igst)\s*@?\s*([0-9]{1,2}(?:\.[0-9]{1,2})?)%?\s*(?:[:\-])?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)
TAX_TYPE_RE = re.compile(
    r"(cgst|sgst|igst)\s*@?\s*([0-9]{1,2}(?:\.[0-9]{1,2})?)%?",
    re.IGNORECASE,
)

DATE_PATTERNS = [
    ("%d-%m-%Y", re.compile(r"\b(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])-(20[0-9]{2})\b")),
    ("%d/%m/%Y", re.compile(r"\b(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/(20[0-9]{2})\b")),
    ("%Y-%m-%d", re.compile(r"\b(20[0-9]{2})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])\b")),
    ("%Y/%m/%d", re.compile(r"\b(20[0-9]{2})/(0[1-9]|1[0-2])/(0[1-9]|[12][0-9]|3[01])\b")),
]


def _ensure_warnings(result: Dict[str, Any]) -> List[str]:
    warnings = result.get("warnings")
    if warnings is None:
        warnings = []
        result["warnings"] = warnings
    return warnings


def apply_invoice_fallbacks(result: Dict[str, Any], text: str) -> Dict[str, Any]:
    warnings = _ensure_warnings(result)

    inv_field = result.get("invoice_number")
    if not inv_field:
        fallback = extract_invoice_number(text)
        if fallback:
            result["invoice_number"] = {"value": fallback, "confidence": 0.55}
            warnings.append("invoice_number_from_fallback_regex")

    if not result.get("date"):
        fallback_date = extract_invoice_date(text)
        if fallback_date:
            result["date"] = {"value": fallback_date, "confidence": 0.55}
            warnings.append("invoice_date_from_fallback_regex")

    needs_subtotal = result.get("subtotal") in (None, "", [])
    needs_total = result.get("total") in (None, "", [])
    subtotal = total = None
    if needs_subtotal or needs_total:
        subtotal, total = extract_amounts(text)
        if needs_subtotal and subtotal is not None:
            result["subtotal"] = subtotal
            warnings.append("subtotal_from_fallback_regex")
        if needs_total and total is not None:
            result["total"] = total
            warnings.append("total_from_fallback_regex")

    taxes_existing = result.get("taxes") or []
    bound = result.get("subtotal") or result.get("total")
    taxes = extract_tax_lines(text, bound)
    if taxes:
        result["taxes"] = taxes_existing + taxes
        warnings.append("taxes_from_fallback_regex")

    _flatten_confidence_field(result, "invoice_number")
    _flatten_confidence_field(result, "date")

    return result


def extract_invoice_number(text: str) -> Optional[str]:
    lines = (text or "").splitlines()
    for idx, line in enumerate(lines):
        if "invoice" not in line.lower():
            continue
        match = INVOICE_NO_RE.search(line)
        if match:
            candidate = match.group(1).strip()
            if len(candidate) >= 4 and any(ch.isdigit() for ch in candidate):
                return candidate
        # fallback: number might be on next non-empty line
        for offset in (1, 2):
            if idx + offset >= len(lines):
                continue
            nxt = lines[idx + offset].strip()
            if not nxt or "invoice" in nxt.lower():
                continue
            if len(nxt) >= 4 and any(ch.isdigit() for ch in nxt):
                return nxt
    return None


def extract_invoice_date(text: str) -> Optional[str]:
    content = text or ""
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if "bill date" in line.lower():
            normalized = _match_date_in_line(line)
            if normalized:
                return normalized
            for offset in range(1, 7):
                if idx + offset >= len(lines):
                    break
                nxt = lines[idx + offset].strip()
                if not nxt:
                    continue
                lower_nxt = nxt.lower()
                if "bill date" in lower_nxt or "due date" in lower_nxt:
                    continue
                normalized = _match_date_in_line(nxt)
                if normalized:
                    return normalized
            break

    bill_date = BILL_DATE_RE.search(content)
    if bill_date:
        raw = bill_date.group(1).strip()
        normalized = _normalize_general_date(raw)
        if normalized:
            return normalized

    for fmt, regex in DATE_PATTERNS:
        match = regex.search(content)
        if match:
            try:
                raw = match.group(0)
                normalized = _normalize_date(raw)
                return normalized or datetime.strptime(raw, fmt).date().isoformat()
            except Exception:
                continue
    return None


def extract_amounts(text: str) -> tuple[Optional[float], Optional[float]]:
    lines = (text or "").splitlines()
    subtotal = _extract_amount_by_keyword(lines, {"sub total", "subtotal"})
    total = _extract_amount_by_keyword(
        lines,
        {"grand total", "total rs", "total rs.", "total"},
        exclude={"sub total", "subtotal"},
    )
    if subtotal is None:
        match = SUBTOTAL_RE.search(text or "")
        if match:
            subtotal = _to_number(match.group(1))
    if total is None:
        match = TOTAL_RE.search(text or "")
        if match:
            total = _to_number(match.group(1))
    return subtotal, total


def extract_tax_lines(text: str, upper_bound: Optional[float]) -> List[Dict[str, Any]]:
    taxes: List[Dict[str, Any]] = []
    lines = (text or "").splitlines()
    for idx, line in enumerate(lines):
        match = TAX_LINE_RE.search(line)
        amount = None
        if match:
            amount = _to_number(match.group(3))
        elif any(t in line.lower() for t in ("cgst", "sgst", "igst")):
            match = TAX_TYPE_RE.search(line)
            rate_hint = float(match.group(2)) if match else None
            amount = _consume_numeric_downstream(lines, idx + 1, upper_bound, rate_hint)
        if match and amount is not None:
            tax_type = match.group(1).upper()
            rate = float(match.group(2))
            taxes.append({"type": tax_type, "rate": rate, "amount": amount})
    return taxes


def _to_number(raw: str | None) -> Optional[float]:
    if not raw:
        return None
    try:
        cleaned = raw.replace(",", "").strip()
        return float(cleaned)
    except Exception:
        return None


def evaluate_invoice_quality(result: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    issues: List[str] = []

    has_invoice_number = _has_value(result.get("invoice_number"))
    has_date = _has_value(result.get("date"))
    has_total = result.get("total") not in (None, "", [])
    has_subtotal = result.get("subtotal") not in (None, "", [])
    has_taxes = bool(result.get("taxes"))

    if has_invoice_number:
        score += 2
    else:
        issues.append("missing_invoice_number")

    if has_date:
        score += 2
    else:
        issues.append("missing_date")

    if has_total:
        score += 2
    elif has_subtotal and has_taxes:
        score += 2
    elif has_subtotal:
        score += 1
        issues.append("missing_taxes")
    else:
        issues.append("missing_totals")

    if ((result.get("seller") or {}).get("gstin")):
        score += 1
    else:
        issues.append("missing_seller_gstin")

    if ((result.get("buyer") or {}).get("gstin")):
        score += 1
    else:
        issues.append("missing_buyer_gstin")

    has_amounts = has_total or (has_subtotal and has_taxes)
    is_usable = has_invoice_number and has_date and has_amounts

    return {
        "score": score,
        "issues": issues,
        "is_usable": is_usable,
    }


def _has_value(field: Any) -> bool:
    if field is None:
        return False
    if isinstance(field, dict):
        return bool(field.get("value"))
    return bool(field)


def _normalize_general_date(raw: str) -> Optional[str]:
    raw = raw.strip()
    normalized = _normalize_date(raw)
    if normalized and re.match(r"^\d{4}-\d{2}-\d{2}$", normalized):
        return normalized
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except Exception:
            continue
    return None


def _flatten_confidence_field(result: Dict[str, Any], field: str) -> None:
    data = result.get(field)
    if isinstance(data, dict):
        value = data.get("value")
        conf = data.get("confidence")
        result[field] = value
        meta = result.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            result["meta"] = meta
        meta[f"{field}_confidence"] = conf


def _match_date_in_line(line: str) -> Optional[str]:
    candidates = re.findall(r"[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4}", line)
    for token in candidates:
        normalized = _normalize_general_date(token)
        if normalized:
            return normalized
    for fmt, regex in DATE_PATTERNS:
        match = regex.search(line)
        if match:
            raw = match.group(0)
            normalized = _normalize_general_date(raw)
            if normalized:
                return normalized
    return None


def _extract_amount_by_keyword(lines: List[str], keywords: set[str], exclude: Optional[set[str]] = None) -> Optional[float]:
    lowered_keywords = {k.lower() for k in keywords}
    excluded = {e.lower() for e in (exclude or set())}
    for idx, line in enumerate(lines):
        lower = line.lower()
        if excluded and any(ex in lower for ex in excluded):
            continue
        if not any(_keyword_in_line(lower, key) for key in lowered_keywords):
            continue
        match = re.search(r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", line)
        if match and _looks_like_amount(match.group(1)):
            return _to_number(match.group(1))
        for offset in range(1, 8):
            if idx + offset >= len(lines):
                break
            nxt = lines[idx + offset].strip()
            if not nxt:
                continue
            if any(_keyword_in_line(nxt.lower(), key) for key in lowered_keywords):
                continue
            match = re.search(r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", nxt)
            if match and _looks_like_amount(match.group(1)):
                return _to_number(match.group(1))
    return None


def _looks_like_amount(token: str) -> bool:
    digits = token.replace(",", "").replace(".", "")
    return len(digits) >= 4


def _keyword_in_line(line: str, keyword: str) -> bool:
    return re.search(rf"\b{re.escape(keyword)}\b", line) is not None


def _consume_numeric_downstream(
    lines: List[str],
    start_idx: int,
    upper_bound: Optional[float],
    rate: Optional[float],
) -> Optional[float]:
    for idx in range(start_idx, min(len(lines), start_idx + 10)):
        nxt = lines[idx].strip()
        if not nxt:
            continue
        match = re.search(r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", nxt)
        if match and _looks_like_amount(match.group(1)):
            value = _to_number(match.group(1))
            if value is None:
                continue
            if upper_bound is not None and rate is not None:
                expected_max = upper_bound * (rate / 100.0 + 0.05)
                if value > expected_max:
                    continue
            return value
    return None

