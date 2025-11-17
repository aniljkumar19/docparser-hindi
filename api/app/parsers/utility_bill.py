# api/app/parsers/utility_bill.py
import re
from datetime import datetime

AMOUNT = r"([₹$]?\s*[0-9][0-9,]*(?:\.[0-9]{2})?)"
DATE    = r"((?:\d{4}[-/]\d{1,2}[-/]\d{1,2})|(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}))"

AMOUNT_DUE_REGEX  = re.compile(r"(?i)\b(amount\s*due|total\s*due|balance\s*due)\b[^0-9$₹]*" + AMOUNT)
DUE_DATE_REGEX    = re.compile(r"(?i)\b(due\s*date|last\s*date\s*to\s*pay)\b[^0-9]*" + DATE)
ACCOUNT_REGEX     = re.compile(r"(?i)\b(account\s*(?:no|number|#))\b[:\-\s]*([A-Z0-9\-]{5,})")
SERVICE_REGEX     = re.compile(r"(?i)\b(service\s*(?:period|from|to))\b[:\-\s]*(.+)")

def _to_number(s: str | None):
    if not s: return None
    s = s.replace("₹","").replace("$","").replace(",","").strip()
    try: return float(s)
    except: return None

def _normalize_date(s: str | None) -> str | None:
    if not s: return None
    s = s.strip()
    for fmt in ("%Y-%m-%d","%Y/%m/%d","%d-%m-%Y","%d/%m/%Y","%m-%d-%Y","%m/%d/%Y","%d-%m-%y","%d/%m/%y"):
        try: return datetime.strptime(s, fmt).date().isoformat()
        except: pass
    return s

def parse_text_rules(text: str) -> dict:
    out = {
        "provider": {},           # {"name": "..."}
        "account_number": None,
        "service_period": None,   # free text for now
        "due_date": None,
        "amount_due": None,
        "currency": "INR" if "₹" in text else ("USD" if "$" in text else None),
        "warnings": []
    }

    # provider guess: first non-empty line
    for line in (l.strip() for l in text.splitlines()):
        if line:
            out["provider"]["name"] = line
            break

    m = ACCOUNT_REGEX.search(text)
    if m: out["account_number"] = m.group(2)

    m = DUE_DATE_REGEX.search(text)
    if m: out["due_date"] = _normalize_date(m.group(2))

    m = AMOUNT_DUE_REGEX.search(text)
    if m: out["amount_due"] = _to_number(m.group(2))

    m = SERVICE_REGEX.search(text)
    if m: out["service_period"] = m.group(2).strip()

    return out
