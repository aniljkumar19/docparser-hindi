# api/app/parsers/receipt_hindi.py
# Hindi parsing rules for receipts
import re
from datetime import datetime

AMOUNT = r"([₹$]?\s*[0-9][0-9,]*(?:\.[0-9]{2})?)"
DATE = r"((?:\d{4}[-/]\d{1,2}[-/]\d{1,2})|(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}))"

# Hindi patterns: कुल, कुल राशि, टोटल, राशि देय
TOTAL_REGEX_HINDI = re.compile(
    r'(?:कुल|कुल\s*राशि|टोटल|total|amount\s*due|grand\s*total)\b[^0-9$₹]*' + AMOUNT,
    re.I | re.UNICODE
)
TOTAL_REGEX = re.compile(r"(?i)\b(total|amount\s*due|grand\s*total)\b[^0-9$₹]*" + AMOUNT)

# Hindi: उप-कुल, सबटोटल
SUB_REGEX_HINDI = re.compile(
    r'(?:उप[-\s]*कुल|सबटोटल|sub\s*total|subtotal)\b[^0-9$₹]*' + AMOUNT,
    re.I | re.UNICODE
)
SUB_REGEX = re.compile(r"(?i)\b(sub\s*total|subtotal)\b[^0-9$₹]*" + AMOUNT)

# Hindi tax: सीजीएसटी, एसजीएसटी, आईजीएसटी, कर, जीएसटी
TAX_REGEX_HINDI = re.compile(
    r'(?:सीजीएसटी|एसजीएसटी|आईजीएसटी|कर|जीएसटी|cgst|sgst|igst|tax|vat|gst)\b[^0-9$₹]*' + AMOUNT,
    re.I | re.UNICODE
)
TAX_REGEX = re.compile(r"(?i)\b(cgst|sgst|igst|tax|vat|gst)\b[^0-9$₹]*" + AMOUNT)

DATE_REGEX = re.compile(DATE)
CURRENCY_SYM = re.compile(r"[₹$]")

def _to_number(s: str | None):
    if not s:
        return None
    s = s.replace("₹", "").replace("$", "").replace(",", "").replace("रु", "").replace("रुपये", "").strip()
    try:
        return float(s)
    except:
        return None

def _first_nonempty_line(text: str) -> str | None:
    # Hindi: रसीद, चालान, बिल, कर चालान
    skip_patterns = (
        "tax invoice", "invoice", "receipt", "gst", "bill",
        "रसीद", "चालान", "बिल", "कर चालान", "टैक्स इनवॉइस"
    )
    for line in (l.strip() for l in text.splitlines()):
        if line and not any(line.lower().startswith(p.lower()) for p in skip_patterns):
            return line
    return None

def parse_text_rules_hindi(text: str) -> dict:
    """Parse Hindi receipt text using Hindi and English patterns."""
    out = {
        "merchant": {},
        "date": None,
        "currency": None,
        "subtotal": None,
        "taxes": [],
        "total": None,
        "line_items": [],
        "warnings": []
    }

    # merchant guess: first meaningful line
    mname = _first_nonempty_line(text)
    if mname:
        out["merchant"]["name"] = mname

    # currency
    out["currency"] = "INR" if "₹" in text or "रु" in text or "रुपये" in text else ("USD" if "$" in text else None)

    # amounts (try Hindi first, then English)
    m = SUB_REGEX_HINDI.search(text) or SUB_REGEX.search(text)
    if m:
        out["subtotal"] = _to_number(m.group(1) if m.lastindex >= 1 else None)
    
    # Tax extraction (try Hindi first, then English)
    for t in TAX_REGEX_HINDI.finditer(text):
        tax_type = t.group(1).upper() if t.lastindex >= 1 else "TAX"
        amount = _to_number(t.group(2) if t.lastindex >= 2 else None)
        if amount:
            out["taxes"].append({"type": tax_type, "amount": amount})
    
    for t in TAX_REGEX.finditer(text):
        tax_type = t.group(1).upper() if t.lastindex >= 1 else "TAX"
        amount = _to_number(t.group(2) if t.lastindex >= 2 else None)
        if amount:
            # Avoid duplicates
            if not any(tax["type"] == tax_type and tax["amount"] == amount for tax in out["taxes"]):
                out["taxes"].append({"type": tax_type, "amount": amount})
    
    m = TOTAL_REGEX_HINDI.search(text) or TOTAL_REGEX.search(text)
    if m:
        out["total"] = _to_number(m.group(1) if m.lastindex >= 1 else None)

    # date
    d = DATE_REGEX.search(text)
    if d:
        raw = d.group(1)
        try:
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%m-%d-%Y", "%m/%d/%Y", "%d-%m-%y", "%d/%m/%y"):
                try:
                    out["date"] = {"value": datetime.strptime(raw, fmt).date().isoformat(), "confidence": 0.7}
                    break
                except:
                    pass
        except:
            pass

    # simple line-items: lines that end with an amount
    LINE_QxU = re.compile(
        r"^(?P<desc>.+?)\s+(?P<qty>\d+(?:\.\d+)?)\s*[x×]\s*"
        r"(?P<unit>[₹$]?\s*[0-9][0-9,]*(?:\.[0-9]{2})?)\s*(?:=|→)\s*"
        r"(?P<amt>[₹$]?\s*[0-9][0-9,]*(?:\.[0-9]{2})?)$"
    )
    LINE_ENDS_WITH_AMT = re.compile(
        r"^(?P<desc>.+?)\s+(?P<amt>[₹$]?\s*[0-9][0-9,]*(?:\.[0-9]{2})?)$"
    )
    # Hindi skip words: कुल, उप-कुल, कर, जीएसटी
    SKIP_WORDS = re.compile(
        r"(?i)\b(subtotal|total|tax|gst|cgst|sgst|igst|amount due|कुल|उप[-\s]*कुल|कर|जीएसटी)\b",
        re.UNICODE
    )

    for raw in text.splitlines():
        line = raw.strip()
        if not line or SKIP_WORDS.search(line):
            continue

        m = LINE_QxU.match(line)
        if m:
            desc = m.group("desc").strip(" -•—")
            qty = float(m.group("qty"))
            unit = _to_number(m.group("unit"))
            amt = _to_number(m.group("amt")) or (qty * (unit or 0.0))
            if unit is not None:
                out["line_items"].append({
                    "desc": desc, "qty": qty, "unit_price": unit, "amount": round(amt, 2)
                })
            continue

        m = LINE_ENDS_WITH_AMT.match(line)
        if m:
            desc = m.group("desc").strip(" -•—")
            amt = _to_number(m.group("amt"))
            if amt is not None:
                out["line_items"].append({
                    "desc": desc, "qty": 1, "unit_price": amt, "amount": round(amt, 2)
                })

    # backfill subtotal if missing
    if out.get("subtotal") is None and out["line_items"]:
        out["subtotal"] = round(sum(i["amount"] for i in out["line_items"]), 2)
    
    return out

