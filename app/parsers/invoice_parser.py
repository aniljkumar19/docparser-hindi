import io, os, time
from typing import Tuple
from pdfminer.high_level import extract_text
from PIL import Image
import pytesseract

from ..schemas import ParseResult, LineItem, TaxLine, TextField
from ..utils import (
    INVOICE_NO_REGEX, DATE_REGEX, GSTIN_REGEX, CURRENCY_REGEX,
    TOTAL_REGEX, SUBTOTAL_REGEX, CGST_REGEX, SGST_REGEX, IGST_REGEX,
    find_first, to_number
)

ENABLE_OCR = os.getenv("ENABLE_OCR","true").lower() == "true"

def _extract_text_from_image(data: bytes) -> Tuple[str, bool]:
    ocr_used = False
    text = ""
    try:
        img = Image.open(io.BytesIO(data))
        if ENABLE_OCR:
            text = pytesseract.image_to_string(img)
            ocr_used = True
    except Exception:
        text = ""
    return text, ocr_used

def _extract_text_from_pdf(data: bytes) -> Tuple[str, bool]:
    try:
        text = extract_text(io.BytesIO(data))
        if text and text.strip():
            return text, False
    except Exception:
        pass
    return "", False

def _extract_text_from_txt(data: bytes) -> Tuple[str, bool]:
    try:
        return data.decode("utf-8", errors="ignore"), False
    except Exception:
        return "", False

def extract_text_auto(filename: str, data: bytes) -> Tuple[str, bool]:
    fname = filename.lower()
    if fname.endswith(".pdf"):
        return _extract_text_from_pdf(data)
    if any(fname.endswith(x) for x in [".png",".jpg",".jpeg",".bmp"]):
        return _extract_text_from_image(data)
    if fname.endswith(".txt"):
        return _extract_text_from_txt(data)
    try:
        return _extract_text_from_pdf(data)
    except Exception:
        return "", False

def parse_invoice_text(text: str) -> ParseResult:
    result = ParseResult()
    inv_no = find_first(INVOICE_NO_REGEX, text)
    if inv_no:
        result.invoice_number = TextField(value=inv_no, confidence=0.9)
    date = find_first(DATE_REGEX, text)
    if date:
        result.date = TextField(value=_normalize_date(date), confidence=0.8)
    gstins = GSTIN_REGEX.findall(text)
    if gstins:
        seller_gstin = gstins[0]
        buyer_gstin = gstins[1] if len(gstins) > 1 else None
        result.seller = {"name": None, "gstin": seller_gstin}
        result.buyer = {"name": None, "gstin": buyer_gstin}
    cur = find_first(CURRENCY_REGEX, text)
    if cur == "₹": cur = "INR"
    result.currency = cur or "INR"
    subtotal = find_first(SUBTOTAL_REGEX, text) or ""
    total = find_first(TOTAL_REGEX, text) or ""
    result.subtotal = to_number(subtotal) if subtotal else None
    result.total = to_number(total) if total else None
    for pat, label in [(CGST_REGEX,"CGST"),(SGST_REGEX,"SGST"),(IGST_REGEX,"IGST")]:
        for m in pat.finditer(text):
            from ..utils import to_number
            rate = to_number(m.group(1)) or 0.0
            amt = to_number(m.group(2)) or 0.0
            result.taxes.append(TaxLine(type=label, rate=rate, amount=amt))
    lines = []
    for raw in text.splitlines():
        raw2 = raw.strip()
        if " x " in raw2 and "=" in raw2:
            try:
                left, right = raw2.split("=", 1)
                amount = to_number(right.strip())
                import re
                nums = re.findall(r"([0-9]+(?:\.[0-9]+)?)", left.replace(",",""))
                qty = float(nums[-2]) if len(nums) >= 2 else 1.0
                unit_price = float(nums[-1]) if len(nums) >= 1 else 0.0
                desc = left.split("-")[0].strip()
                lines.append(LineItem(desc=desc, qty=qty, unit_price=unit_price, amount=amount or qty*unit_price))
            except Exception:
                continue
    result.line_items = lines
    if result.subtotal is None and lines:
        result.subtotal = round(sum(li.amount for li in lines), 2)
    if result.total is None and result.subtotal is not None and result.taxes:
        tax_sum = round(sum(t.amount for t in result.taxes), 2)
        result.total = round(result.subtotal + tax_sum, 2)
    return result

def _normalize_date(s: str) -> str:
    s2 = s.replace(".","-").replace("/","-")
    import re
    m_iso = re.match(r"(20[0-9]{2})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$", s2)
    if m_iso: return s2
    m_dmy = re.match(r"(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])-(20[0-9]{2})$", s2)
    if m_dmy:
        d, m, y = m_dmy.groups()
        return f"{y}-{m}-{d}"
    return s
