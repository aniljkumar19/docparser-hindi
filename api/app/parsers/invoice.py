import io, time
from pdfminer.high_level import extract_text
from PIL import Image
import pytesseract

# SAFE import with callable fallback
try:
    from .detect import detect_doc_type as _detect_doc_type
except Exception:
    _detect_doc_type = None  # will replace below

# if import failed OR something overwrote it (e.g., a string), use a function
if not callable(_detect_doc_type):
    def _detect_doc_type(_: str) -> str:
        return "invoice"



from .rules import parse_text_rules

def parse_bytes_to_result(filename: str, data: bytes):
    t0 = time.time()

    text = ""
    ocr_used = False

    # 1) Try pdfminer text first
    try:
        text = extract_text(io.BytesIO(data)) or ""
    except Exception:
        text = ""

    # 2) If text is very short/empty, try OCR once
    if len(text.strip()) < 60:
        t2 = ""
        try:
            img = Image.open(io.BytesIO(data))
            t2 = pytesseract.image_to_string(img) or ""
        except Exception:
            t2 = ""
        if len(t2.strip()) > len(text.strip()):
            text = t2
            ocr_used = True

    # 3) Doc-type detection (single call). Bail early if not an invoice.
    doc_type = _detect_doc_type(text)
    if doc_type != "invoice":
        dt = int((time.time() - t0) * 1000)
        meta = {
            "pages": 1,
            "ocr_used": ocr_used,
            "processing_ms": dt,
            "detected_doc_type": doc_type,
        }
        result = {
            "invoice_number": None,
            "date": None,
            "seller": {},
            "buyer": {},
            "currency": None,
            "subtotal": None,
            "taxes": [],
            "total": None,
            "line_items": [],
            "warnings": [f"Unsupported document type: {doc_type}"],
        }
        return result, meta

    # 4) Normal invoice parsing
    result = parse_text_rules(text)
    dt = int((time.time() - t0) * 1000)
    meta = {
        "pages": 1,
        "ocr_used": ocr_used,
        "processing_ms": dt,
        "detected_doc_type": "invoice",
    }
    return result, meta
    

