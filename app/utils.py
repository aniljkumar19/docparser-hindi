import re
from typing import Optional

GSTIN_REGEX = re.compile(r"""\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b""")
INVOICE_NO_REGEX = re.compile(r"""(?:Invoice\s*(?:No\.?|#)\s*[:\-]?\s*|Inv(?:\.|#)?\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)""", re.IGNORECASE)
DATE_REGEX = re.compile(r"""\b(20[0-9]{2}[-/\.](0[1-9]|1[0-2])[-/\.](0[1-9]|[12][0-9]|3[01])|
(0[1-9]|[12][0-9]|3[01])[-/\.](0[1-9]|1[0-2])[-/\.](20[0-9]{2}))\b""", re.VERBOSE)
CURRENCY_REGEX = re.compile(r"""\b(INR|USD|EUR|₹|\$|€)\b""")
TOTAL_REGEX = re.compile(r"""\bTotal\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b""", re.IGNORECASE)
SUBTOTAL_REGEX = re.compile(r"""\bSub\s*Total|Subtotal\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b""", re.IGNORECASE)
CGST_REGEX = re.compile(r"""\bCGST\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)""", re.IGNORECASE)
SGST_REGEX = re.compile(r"""\bSGST\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)""", re.IGNORECASE)
IGST_REGEX = re.compile(r"""\bIGST\s*\(?(\d{1,2}(?:\.\d)?)%\)?\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)""", re.IGNORECASE)

def find_first(pattern: re.Pattern, text: str) -> Optional[str]:
    m = pattern.search(text)
    if m:
        if m.groups():
            return m.group(m.lastindex or 1)
        return m.group(0)
    return None

def to_number(s: str) -> Optional[float]:
    try:
        s = s.replace(",", "").replace("₹","");
        return float(s)
    except Exception:
        return None
