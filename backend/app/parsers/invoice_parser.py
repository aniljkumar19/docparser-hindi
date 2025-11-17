import io, os, time
from typing import Tuple, List
from pdfminer.high_level import extract_text
from PIL import Image
import pytesseract

from .utils import (
    INVOICE_NO_REGEX, DATE_REGEX, GSTIN_REGEX, CURRENCY_REGEX,
    TOTAL_REGEX, SUBTOTAL_REGEX, CGST_REGEX, SGST_REGEX, IGST_REGEX,
    find_first, to_number, normalize_date
)

ENABLE_OCR = os.getenv("ENABLE_OCR","true").lower() == "true"
ENABLE_CAMELOT = os.getenv("ENABLE_CAMELOT","true").lower() == "true"

def _ocr_image_bytes(data: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img)
    except Exception:
        return ""

def _pdf_text_bytes(data: bytes) -> Tuple[str, bool]:
    # Try direct text extraction
    try:
        text = extract_text(io.BytesIO(data))
        if text and text.strip():
            return text, False
    except Exception:
        pass
    # Fallback: OCR not implemented per-page here
    return "", False

def extract_text_auto(filename: str, data: bytes) -> Tuple[str, bool]:
    fn = filename.lower()
    if fn.endswith(".pdf"):
        return _pdf_text_bytes(data)
    if any(fn.endswith(x) for x in [".png",".jpg",".jpeg",".bmp"]):
        if ENABLE_OCR:
            return _ocr_image_bytes(data), True
        return "", False
    try:
        return data.decode("utf-8", errors="ignore"), False
    except Exception:
        return "", False

def parse_invoice_text(text: str) -> dict:
    result = {
        "invoice_number": None,
        "date": None,
        "seller": None,
        "buyer": None,
        "currency": "INR",
        "subtotal": None,
        "taxes": [],
        "total": None,
        "line_items": [],
        "warnings": []
    }

    inv_no = find_first(INVOICE_NO_REGEX, text)
    if inv_no:
        result["invoice_number"] = {"value": inv_no, "confidence": 0.9}

    date = find_first(DATE_REGEX, text)
    if date:
        result["date"] = {"value": normalize_date(date), "confidence": 0.8}

    gstins = GSTIN_REGEX.findall(text)
    if gstins:
        seller = {"name": None, "gstin": gstins[0]}
        buyer = {"name": None, "gstin": gstins[1]} if len(gstins) > 1 else None
        result["seller"] = seller
        result["buyer"] = buyer

    cur = find_first(CURRENCY_REGEX, text)
    if cur == "₹": cur = "INR"
    result["currency"] = cur or "INR"

    subtotal = find_first(SUBTOTAL_REGEX, text) or ""
    total = find_first(TOTAL_REGEX, text) or ""
    result["subtotal"] = to_number(subtotal) if subtotal else None
    result["total"] = to_number(total) if total else None

    for pat, label in [(CGST_REGEX,"CGST"),(SGST_REGEX,"SGST"),(IGST_REGEX,"IGST")]:
        for m in pat.finditer(text):
            from .utils import to_number
            rate = to_number(m.group(1)) or 0.0
            amt = to_number(m.group(2)) or 0.0
            result["taxes"].append({"type": label, "rate": rate, "amount": amt})

    # Very naive line item extraction (same as MVP)
    for raw in text.splitlines():
        raw2 = raw.strip()
        if " x " in raw2 and "=" in raw2:
            try:
                left, right = raw2.split("=", 1)
                amount = to_number(right.strip()) or None
                import re
                nums = re.findall(r"([0-9]+(?:\.[0-9]+)?)", left.replace(",",""))
                qty = float(nums[-2]) if len(nums) >= 2 else 1.0
                unit_price = float(nums[-1]) if len(nums) >= 1 else 0.0
                desc = left.split("-")[0].strip()
                result["line_items"].append({"desc": desc, "qty": qty, "unit_price": unit_price, "amount": amount or qty*unit_price})
            except Exception:
                continue

    if result["subtotal"] is None and result["line_items"]:
        result["subtotal"] = round(sum(li["amount"] for li in result["line_items"]), 2)
    if result["total"] is None and result["subtotal"] is not None and result["taxes"]:
        tax_sum = round(sum(t["amount"] for t in result["taxes"]), 2)
        result["total"] = round(result["subtotal"] + tax_sum, 2)

    return result
