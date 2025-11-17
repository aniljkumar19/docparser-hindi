import re
from datetime import datetime

def _to_number(s):
    try:
        return float(s.replace(",","").replace("₹","").replace("$","").strip())
    except Exception:
        return None

GSTIN_REGEX = re.compile(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b")
INVOICE_NO_REGEX = re.compile(
    r'\b(?:invoice|inv|bill)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{4,})\b',
    re.I
)

DATE_REGEX = re.compile(r"\b(20[0-9]{2}[-\/.](0[1-9]|1[0-2])[-\/.](0[1-9]|[12][0-9]|3[01])|(0[1-9]|[12][0-9]|3[01])[-\/.](0[1-9]|1[0-2])[-\/.](20[0-9]{2}))\b")

TOTAL_REGEX = re.compile(r"\bTotal\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)
SUBTOTAL_REGEX = re.compile(r"\bSub\s*Total|Subtotal\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)
# Enhanced GST tax patterns for Indian market
CGST_REGEX = re.compile(r"\bCGST\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)
SGST_REGEX = re.compile(r"\bSGST\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)
IGST_REGEX = re.compile(r"\bIGST\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)

# Additional Indian tax patterns
CESS_REGEX = re.compile(r"\bCESS\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)
TDS_REGEX = re.compile(r"\bTDS\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)
TCS_REGEX = re.compile(r"\bTCS\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)

# GST rate patterns (common Indian rates: 0%, 5%, 12%, 18%, 28%)
GST_RATE_REGEX = re.compile(r"\b(?:GST|Tax)\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)

# HSN/SAC code patterns (for GST classification)
HSN_REGEX = re.compile(r"\bHSN\s*[:\-]?\s*([0-9]{4,8})\b", re.IGNORECASE)
SAC_REGEX = re.compile(r"\bSAC\s*[:\-]?\s*([0-9]{4,8})\b", re.IGNORECASE)

def normalize_date(s: str) -> str | None:
    if not s:
        return None
    s = s.strip()
    # try a few common formats; extend as needed
    for fmt in ("%Y-%m-%d","%Y/%m/%d",
                "%d-%m-%Y","%d/%m/%Y",
                "%m-%d-%Y","%m/%d/%Y",
                "%d-%m-%y","%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return s

def parse_text_rules(text: str) -> dict:
    out = {"invoice_number": None, "date": None, "seller": {}, "buyer": {}, "currency": "INR",
           "subtotal": None, "taxes": [], "total": None, "line_items": [], "warnings": []}

    warnings = out.get("warnings") or []
    m = INVOICE_NO_REGEX.search(text)
    inv_value = None
    if m:
        cand = (m.group(1) or "").strip()
        # simple sanity: at least 5 chars and not purely alphabetic
        if len(cand) >= 5 and not cand.isalpha():
            inv_value = cand
        else:
            warnings.append("invoice_number_low_confidence")

    if inv_value:
        out["invoice_number"] = {"value": inv_value, "confidence": 0.9}
    out["warnings"] = warnings


    dt = DATE_REGEX.search(text)
    if dt:
        out["date"] = {"value": normalize_date(dt.group(0)), "confidence": 0.8}

    gstins = GSTIN_REGEX.findall(text)
    if gstins:
        out["seller"] = {"gstin": gstins[0]}
        if len(gstins) > 1:
            out["buyer"] = {"gstin": gstins[1]}

    m = SUBTOTAL_REGEX.search(text)
    if m: out["subtotal"] = _to_number(m.group(1))
    m = TOTAL_REGEX.search(text)
    if m: out["total"] = _to_number(m.group(1))

    # Enhanced Indian tax parsing
    tax_patterns = [
        (CGST_REGEX, "CGST"), (SGST_REGEX, "SGST"), (IGST_REGEX, "IGST"),
        (CESS_REGEX, "CESS"), (TDS_REGEX, "TDS"), (TCS_REGEX, "TCS"),
        (GST_RATE_REGEX, "GST")
    ]
    
    for pat, typ in tax_patterns:
        for m in pat.finditer(text):
            rate = _to_number(m.group(1)) or 0.0
            amt = _to_number(m.group(2)) or 0.0
            out["taxes"].append({"type": typ, "rate": rate, "amount": amt})
    
    # Extract HSN/SAC codes for GST classification
    hsn_codes = HSN_REGEX.findall(text)
    sac_codes = SAC_REGEX.findall(text)
    if hsn_codes:
        out["hsn_codes"] = hsn_codes
    if sac_codes:
        out["sac_codes"] = sac_codes

    # naive line item heuristic
    for line in text.splitlines():
        if " x " in line and "=" in line:
            try:
                left, right = line.split("=",1)
                amt = _to_number(right)
                nums = re.findall(r"([0-9]+(?:\.[0-9]+)?)", left.replace(",",""))
                qty = float(nums[-2]) if len(nums) >= 2 else 1.0
                unit = float(nums[-1]) if len(nums) >= 1 else 0.0
                desc = left.split("-")[0].strip()
                out["line_items"].append({"desc": desc, "qty": qty, "unit_price": unit, "amount": amt or qty*unit})
            except Exception:
                continue

    if out["subtotal"] is None and out["line_items"]:
        out["subtotal"] = round(sum(i["amount"] for i in out["line_items"]), 2)
    if out["total"] is None and out["subtotal"] is not None and out["taxes"]:
        tax_sum = round(sum(t["amount"] for t in out["taxes"]), 2)
        out["total"] = round(out["subtotal"] + tax_sum, 2)

    return out
