# api/app/parsers/receipt.py
import re
from datetime import datetime

AMOUNT = r"([₹$]?\s*[0-9][0-9,]*(?:\.[0-9]{2})?)"
DATE    = r"((?:\d{4}[-/]\d{1,2}[-/]\d{1,2})|(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}))"
TOTAL_REGEX  = re.compile(r"(?i)\b(total|amount\s*due|grand\s*total)\b[^0-9$₹]*" + AMOUNT)
SUB_REGEX    = re.compile(r"(?i)\b(sub\s*total|subtotal)\b[^0-9$₹]*" + AMOUNT)
TAX_REGEX    = re.compile(r"(?i)\b(cgst|sgst|igst|tax|vat|gst)\b[^0-9$₹]*" + AMOUNT)
DATE_REGEX   = re.compile(DATE)
CURRENCY_SYM = re.compile(r"[₹$]")

def _to_number(s: str | None):
    if not s: return None
    s = s.replace("₹","").replace("$","").replace(",","").strip()
    try: return float(s)
    except: return None

def _first_nonempty_line(text: str) -> str | None:
    for line in (l.strip() for l in text.splitlines()):
        if line and not line.lower().startswith(("tax invoice","invoice","receipt","gst","bill")):
            return line
    return None

def parse_text_rules(text: str) -> dict:
    out = {"merchant": {}, "date": None, "currency": None,
           "subtotal": None, "taxes": [], "total": None,
           "line_items": [], "warnings": []}

    # merchant guess: first meaningful line
    mname = _first_nonempty_line(text)
    if mname:
        out["merchant"]["name"] = mname

    # currency
    out["currency"] = "INR" if "₹" in text else ("USD" if "$" in text else None)

    # amounts
    m = SUB_REGEX.search(text)
    if m: out["subtotal"] = _to_number(m.group(2))
    for t in TAX_REGEX.finditer(text):
        out["taxes"].append({"type": t.group(1).upper(), "amount": _to_number(t.group(2))})
    m = TOTAL_REGEX.search(text)
    if m: out["total"] = _to_number(m.group(2))

    # date
    d = DATE_REGEX.search(text)
    if d:
        raw = d.group(1)
        try:
            for fmt in ("%Y-%m-%d","%Y/%m/%d","%d-%m-%Y","%d/%m/%Y","%m-%d-%Y","%m/%d/%Y","%d-%m-%y","%d/%m/%y"):
                try:
                    out["date"] = {"value": datetime.strptime(raw, fmt).date().isoformat(), "confidence": 0.7}
                    break
                except: pass
        except: pass

    # simple line-items: lines that end with an amount
    # ---- improved line-items ----
    LINE_QxU = re.compile(
        r"^(?P<desc>.+?)\s+(?P<qty>\d+(?:\.\d+)?)\s*[x×]\s*"
        r"(?P<unit>[₹$]?\s*[0-9][0-9,]*(?:\.[0-9]{2})?)\s*(?:=|→)\s*"
        r"(?P<amt>[₹$]?\s*[0-9][0-9,]*(?:\.[0-9]{2})?)$"
    )
    LINE_ENDS_WITH_AMT = re.compile(
        r"^(?P<desc>.+?)\s+(?P<amt>[₹$]?\s*[0-9][0-9,]*(?:\.[0-9]{2})?)$"
    )
    SKIP_WORDS = re.compile(r"(?i)\b(subtotal|total|tax|gst|cgst|sgst|igst|amount due)\b")

    for raw in text.splitlines():
        line = raw.strip()
        if not line or SKIP_WORDS.search(line):
            continue

        m = LINE_QxU.match(line)
        if m:
            desc = m.group("desc").strip(" -•—")
            qty  = float(m.group("qty"))
            unit = _to_number(m.group("unit"))
            amt  = _to_number(m.group("amt")) or (qty * (unit or 0.0))
            if unit is not None:
                out["line_items"].append({
                    "desc": desc, "qty": qty, "unit_price": unit, "amount": round(amt, 2)
                })
            continue

        m = LINE_ENDS_WITH_AMT.match(line)
        if m:
            desc = m.group("desc").strip(" -•—")
            amt  = _to_number(m.group("amt"))
            if amt is not None:
                out["line_items"].append({
                    "desc": desc, "qty": 1, "unit_price": amt, "amount": round(amt, 2)
                })

    # backfill subtotal if missing
    if out.get("subtotal") is None and out["line_items"]:
        out["subtotal"] = round(sum(i["amount"] for i in out["line_items"]), 2)
    return out
    # ---- end improved line-items ----

