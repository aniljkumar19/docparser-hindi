# api/app/parsers/utility_bill_hindi.py
# Hindi parsing rules for utility bills
import re
from datetime import datetime

AMOUNT = r"([₹$]?\s*[0-9][0-9,]*(?:\.[0-9]{2})?)"
DATE = r"((?:\d{4}[-/]\d{1,2}[-/]\d{1,2})|(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}))"

# Hindi: राशि देय, कुल देय, शेष देय
AMOUNT_DUE_REGEX_HINDI = re.compile(
    r'(?:राशि\s*देय|कुल\s*देय|शेष\s*देय|amount\s*due|total\s*due|balance\s*due)\b[^0-9$₹]*' + AMOUNT,
    re.I | re.UNICODE
)
AMOUNT_DUE_REGEX = re.compile(r"(?i)\b(amount\s*due|total\s*due|balance\s*due)\b[^0-9$₹]*" + AMOUNT)

# Hindi: देय तिथि, अंतिम भुगतान तिथि
DUE_DATE_REGEX_HINDI = re.compile(
    r'(?:देय\s*तिथि|अंतिम\s*भुगतान\s*तिथि|due\s*date|last\s*date\s*to\s*pay)\b[^0-9]*' + DATE,
    re.I | re.UNICODE
)
DUE_DATE_REGEX = re.compile(r"(?i)\b(due\s*date|last\s*date\s*to\s*pay)\b[^0-9]*" + DATE)

# Hindi: खाता संख्या, खाता नंबर
ACCOUNT_REGEX_HINDI = re.compile(
    r'(?:खाता\s*(?:संख्या|नंबर|#)|account\s*(?:no|number|#))\b[:\-\s]*([A-Z0-9\-]{5,})',
    re.I | re.UNICODE
)
ACCOUNT_REGEX = re.compile(r"(?i)\b(account\s*(?:no|number|#))\b[:\-\s]*([A-Z0-9\-]{5,})")

# Hindi: सेवा अवधि
SERVICE_REGEX_HINDI = re.compile(
    r'(?:सेवा\s*अवधि|service\s*(?:period|from|to))\b[:\-\s]*(.+)',
    re.I | re.UNICODE
)
SERVICE_REGEX = re.compile(r"(?i)\b(service\s*(?:period|from|to))\b[:\-\s]*(.+)")

def _to_number(s: str | None):
    if not s:
        return None
    s = s.replace("₹", "").replace("$", "").replace(",", "").replace("रु", "").replace("रुपये", "").strip()
    try:
        return float(s)
    except:
        return None

def _normalize_date(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%m-%d-%Y", "%m/%d/%Y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except:
            pass
    return s

def parse_text_rules_hindi(text: str) -> dict:
    """Parse Hindi utility bill text using Hindi and English patterns."""
    out = {
        "provider": {},
        "account_number": None,
        "service_period": None,
        "due_date": None,
        "amount_due": None,
        "currency": "INR" if "₹" in text or "रु" in text or "रुपये" in text else ("USD" if "$" in text else None),
        "warnings": []
    }

    # provider guess: first non-empty line
    for line in (l.strip() for l in text.splitlines()):
        if line:
            out["provider"]["name"] = line
            break

    # Account number (try Hindi first, then English)
    m = ACCOUNT_REGEX_HINDI.search(text) or ACCOUNT_REGEX.search(text)
    if m:
        out["account_number"] = m.group(1) if m.lastindex >= 1 else None

    # Due date (try Hindi first, then English)
    m = DUE_DATE_REGEX_HINDI.search(text) or DUE_DATE_REGEX.search(text)
    if m:
        date_str = m.group(1) if m.lastindex >= 1 else None
        out["due_date"] = _normalize_date(date_str)

    # Amount due (try Hindi first, then English)
    m = AMOUNT_DUE_REGEX_HINDI.search(text) or AMOUNT_DUE_REGEX.search(text)
    if m:
        out["amount_due"] = _to_number(m.group(1) if m.lastindex >= 1 else None)

    # Service period (try Hindi first, then English)
    m = SERVICE_REGEX_HINDI.search(text) or SERVICE_REGEX.search(text)
    if m:
        out["service_period"] = (m.group(1) if m.lastindex >= 1 else "").strip()

    return out

