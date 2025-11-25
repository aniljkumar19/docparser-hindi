# api/app/parsers/rules_hindi.py
# Hindi parsing rules - regex patterns for Hindi documents
import re
from datetime import datetime

def _to_number(s):
    """Extract number from string, handling Hindi number formats."""
    if not s:
        return None
    try:
        # Remove common Hindi currency symbols and separators
        s = s.replace(",", "").replace("₹", "").replace("$", "").replace("रु", "").replace("रुपये", "")
        s = s.replace(" ", "").strip()
        return float(s)
    except Exception:
        return None

# GSTIN regex (same for Hindi and English)
GSTIN_REGEX = re.compile(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b")

# Hindi invoice number patterns
# Hindi: चालान, बिल, इनवॉइस, चालान संख्या, बिल नंबर
INVOICE_NO_REGEX_HINDI = re.compile(
    r'(?:चालान|बिल|इनवॉइस|invoice|inv|bill)\s*(?:संख्या|नंबर|no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{4,})',
    re.I | re.UNICODE
)

# English invoice number (fallback)
INVOICE_NO_REGEX = re.compile(
    r'\b(?:invoice|inv|bill)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{4,})\b',
    re.I
)

# Date patterns (same format, but may have Hindi labels)
DATE_REGEX = re.compile(
    r"\b(20[0-9]{2}[-\/.](0[1-9]|1[0-2])[-\/.](0[1-9]|[12][0-9]|3[01])|(0[1-9]|[12][0-9]|3[01])[-\/.](0[1-9]|1[0-2])[-\/.](20[0-9]{2}))\b"
)

# Hindi total patterns: कुल, कुल राशि, टोटल
TOTAL_REGEX_HINDI = re.compile(
    r'(?:कुल|कुल\s*राशि|टोटल|total)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)',
    re.I | re.UNICODE
)
TOTAL_REGEX = re.compile(r"\bTotal\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)

# Hindi subtotal patterns: उप-कुल, सबटोटल
SUBTOTAL_REGEX_HINDI = re.compile(
    r'(?:उप[-\s]*कुल|सबटोटल|sub\s*total)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)',
    re.I | re.UNICODE
)
SUBTOTAL_REGEX = re.compile(r"\bSub\s*Total|Subtotal\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)

# Hindi tax patterns
# CGST: सीजीएसटी, CGST
# SGST: एसजीएसटी, SGST  
# IGST: आईजीएसटी, IGST
CGST_REGEX_HINDI = re.compile(
    r'(?:सीजीएसटी|CGST)\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)',
    re.I | re.UNICODE
)
CGST_REGEX = re.compile(r"\bCGST\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)

SGST_REGEX_HINDI = re.compile(
    r'(?:एसजीएसटी|SGST)\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)',
    re.I | re.UNICODE
)
SGST_REGEX = re.compile(r"\bSGST\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)

IGST_REGEX_HINDI = re.compile(
    r'(?:आईजीएसटी|IGST)\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)',
    re.I | re.UNICODE
)
IGST_REGEX = re.compile(r"\bIGST\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)

# Additional tax patterns (CESS, TDS, TCS)
CESS_REGEX = re.compile(r"\bCESS\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)
TDS_REGEX = re.compile(r"\bTDS\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)
TCS_REGEX = re.compile(r"\bTCS\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)

# GST rate patterns
GST_RATE_REGEX = re.compile(r"\b(?:GST|Tax|जीएसटी|कर)\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", re.IGNORECASE | re.UNICODE)

# HSN/SAC codes (same format)
HSN_REGEX = re.compile(r"\bHSN\s*[:\-]?\s*([0-9]{4,8})\b", re.IGNORECASE)
SAC_REGEX = re.compile(r"\bSAC\s*[:\-]?\s*([0-9]{4,8})\b", re.IGNORECASE)

def normalize_date(s: str) -> str | None:
    """Normalize date string to ISO format."""
    if not s:
        return None
    s = s.strip()
    # Try common date formats
    for fmt in ("%Y-%m-%d", "%Y/%m/%d",
                "%d-%m-%Y", "%d/%m/%Y",
                "%m-%d-%Y", "%m/%d/%Y",
                "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return s

def parse_text_rules_hindi(text: str) -> dict:
    """
    Parse Hindi invoice text using Hindi and English patterns.
    Returns structured invoice data.
    """
    out = {
        "invoice_number": None,
        "date": None,
        "seller": {},
        "buyer": {},
        "currency": "INR",
        "subtotal": None,
        "taxes": [],
        "total": None,
        "line_items": [],
        "warnings": []
    }

    warnings = out.get("warnings") or []
    
    # Try Hindi invoice number first, then English
    m = INVOICE_NO_REGEX_HINDI.search(text) or INVOICE_NO_REGEX.search(text)
    inv_value = None
    if m:
        cand = (m.group(1) or "").strip()
        if len(cand) >= 5 and not cand.isalpha():
            inv_value = cand
        else:
            warnings.append("invoice_number_low_confidence")

    if inv_value:
        out["invoice_number"] = {"value": inv_value, "confidence": 0.9}
    out["warnings"] = warnings

    # Date extraction
    dt = DATE_REGEX.search(text)
    if dt:
        out["date"] = {"value": normalize_date(dt.group(0)), "confidence": 0.8}

    # GSTIN extraction
    gstins = GSTIN_REGEX.findall(text)
    if gstins:
        out["seller"] = {"gstin": gstins[0]}
        if len(gstins) > 1:
            out["buyer"] = {"gstin": gstins[1]}

    # Subtotal (try Hindi first, then English)
    m = SUBTOTAL_REGEX_HINDI.search(text) or SUBTOTAL_REGEX.search(text)
    if m:
        out["subtotal"] = _to_number(m.group(1))
    
    # Total (try Hindi first, then English)
    m = TOTAL_REGEX_HINDI.search(text) or TOTAL_REGEX.search(text)
    if m:
        out["total"] = _to_number(m.group(1))

    # Tax extraction (try Hindi patterns first, then English)
    tax_patterns = [
        (CGST_REGEX_HINDI, "CGST"), (CGST_REGEX, "CGST"),
        (SGST_REGEX_HINDI, "SGST"), (SGST_REGEX, "SGST"),
        (IGST_REGEX_HINDI, "IGST"), (IGST_REGEX, "IGST"),
        (CESS_REGEX, "CESS"), (TDS_REGEX, "TDS"), (TCS_REGEX, "TCS"),
        (GST_RATE_REGEX, "GST")
    ]
    
    for pat, typ in tax_patterns:
        for m in pat.finditer(text):
            rate = _to_number(m.group(1)) or 0.0
            amt = _to_number(m.group(2)) or 0.0
            out["taxes"].append({"type": typ, "rate": rate, "amount": amt})
    
    # Extract HSN/SAC codes
    hsn_match = HSN_REGEX.search(text)
    if hsn_match:
        out.setdefault("metadata", {})["hsn"] = hsn_match.group(1)
    
    sac_match = SAC_REGEX.search(text)
    if sac_match:
        out.setdefault("metadata", {})["sac"] = sac_match.group(1)

    return out


