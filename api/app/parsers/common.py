# api/app/parsers/common.py
import io
import re
from typing import List, Tuple

from pdfminer.high_level import extract_text as _pdf_extract
try:
    import pdfplumber
except Exception:
    pdfplumber = None
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None
try:
    from PIL import Image
    import pytesseract
except Exception:
    Image = None
    pytesseract = None

def extract_text_safely(data: bytes, filename: str | None = None) -> Tuple[str, bool]:
    """Return (text, ocr_used). Handles .txt/.csv, PDFs, images."""
    # 1) Plain text files: decode
    if filename and filename.lower().endswith((".txt", ".md", ".csv", ".log")):
        return data.decode("utf-8", errors="ignore"), False

    is_pdf = data[:4] == b"%PDF"
    if is_pdf:
        buffer = io.BytesIO(data)
        try:
            txt = _pdf_extract(buffer) or ""
        except Exception:
            txt = ""

        if txt.strip():
            return txt, False

        # pdfminer found nothing – try pdfplumber
        if pdfplumber is not None:
            try:
                buffer.seek(0)
                with pdfplumber.open(buffer) as pdf:
                    pages = [page.extract_text() or "" for page in pdf.pages]
                txt = "\n".join(pages).strip()
                if txt:
                    return txt, False
            except Exception:
                pass

        # As a last resort, run OCR per page using pdfplumber rendering
        if pdfplumber is not None and Image and pytesseract:
            try:
                buffer.seek(0)
                with pdfplumber.open(buffer) as pdf:
                    texts: list[str] = []
                    for page in pdf.pages:
                        try:
                            page_image = page.to_image(resolution=200)
                            pil_img = getattr(page_image, "original", None) or getattr(page_image, "image", None)
                            if pil_img is None and hasattr(page_image, "pil_image"):
                                pil_img = page_image.pil_image
                            if pil_img is None:
                                continue
                            t = ocr_page(pil_img)
                            if t.strip():
                                texts.append(t)
                        except Exception:
                            continue
                full = "\n".join(texts).strip()
                if full:
                    return full, True
            except Exception:
                pass

        # Fallback to pdf2image OCR if available
        if convert_from_bytes and Image and pytesseract:
            try:
                images = convert_from_bytes(data, dpi=200)
                texts = []
                for img in images:
                    t = ocr_page(img)
                    if t.strip():
                        texts.append(t)
                full = "\n".join(texts).strip()
                if full:
                    return full, True
            except Exception:
                pass

    # 3) Try generic UTF-8 decode (some uploads are text with no extension)
    if not is_pdf:  # raw PDF bytes aren't useful as UTF-8
        try:
            t = data.decode("utf-8", errors="ignore")
            if t.strip():
                return t, False
        except Exception:
            pass

    # 4) Last resort: OCR (images)
    if Image and pytesseract:
        try:
            img = Image.open(io.BytesIO(data))
            t2 = ocr_page(img)
            if t2.strip():
                return t2, True
        except Exception:
            pass

    return "", False


def ocr_page(img, lang: str = "eng") -> str:
    """
    Perform OCR on an image.
    
    Args:
        img: PIL Image object
        lang: Language code(s) for OCR. Use "hin+eng" for Hindi+English mixed documents.
              Options: "eng", "hin", "hin+eng" (default: "eng")
    
    Returns:
        Extracted text string
    """
    if not pytesseract:
        return ""
    
    # Try the requested language, fallback to English if it fails
    try:
        return pytesseract.image_to_string(img, lang=lang, config="--psm 6") or ""
    except Exception:
        # If Hindi language pack not installed, fallback to English
        if lang != "eng":
            try:
                return pytesseract.image_to_string(img, lang="eng", config="--psm 6") or ""
            except Exception:
                return ""
        return ""


def extract_text_safely_hindi(data: bytes, filename: str | None = None) -> Tuple[str, bool]:
    """
    Extract text with Hindi OCR support. Tries Hindi+English OCR if English-only fails.
    Returns (text, ocr_used).
    """
    # First try English extraction
    text, ocr_used = extract_text_safely(data, filename)
    
    # If we got text, return it
    if text.strip():
        return text, ocr_used
    
    # If no text and we haven't tried OCR yet, try Hindi+English OCR
    if not ocr_used and Image and pytesseract:
        is_pdf = data[:4] == b"%PDF"
        
        if is_pdf:
            # Try Hindi OCR on PDF
            if pdfplumber is not None:
                try:
                    buffer = io.BytesIO(data)
                    with pdfplumber.open(buffer) as pdf:
                        texts: list[str] = []
                        for page in pdf.pages:
                            try:
                                page_image = page.to_image(resolution=200)
                                pil_img = getattr(page_image, "original", None) or getattr(page_image, "image", None)
                                if pil_img is None and hasattr(page_image, "pil_image"):
                                    pil_img = page_image.pil_image
                                if pil_img is None:
                                    continue
                                t = ocr_page(pil_img, lang="hin+eng")
                                if t.strip():
                                    texts.append(t)
                            except Exception:
                                continue
                        full = "\n".join(texts).strip()
                        if full:
                            return full, True
                except Exception:
                    pass
            
            # Fallback to pdf2image with Hindi OCR
            if convert_from_bytes and Image and pytesseract:
                try:
                    images = convert_from_bytes(data, dpi=200)
                    texts = []
                    for img in images:
                        t = ocr_page(img, lang="hin+eng")
                        if t.strip():
                            texts.append(t)
                    full = "\n".join(texts).strip()
                    if full:
                        return full, True
                except Exception:
                    pass
        else:
            # Try Hindi OCR on images
            try:
                img = Image.open(io.BytesIO(data))
                t = ocr_page(img, lang="hin+eng")
                if t.strip():
                    return t, True
            except Exception:
                pass
    
    return text, ocr_used


_NUMERIC_TOKEN = re.compile(r"\b[0-9OIl]{2,}(?:[./][0-9OIl]{2,})?\b")


def normalize_text(s: str | None) -> str:
    if not s:
        return ""
    s = s.replace("\xa0", " ").replace("\uf0b7", " ")
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"[ \t]*\n[ \t]*", "\n", s)

    def _fix_token(match: re.Match) -> str:
        token = match.group(0)
        token = token.replace("O", "0").replace("o", "0")
        token = token.replace("I", "1").replace("l", "1")
        return token

    s = _NUMERIC_TOKEN.sub(_fix_token, s)
    return s.strip()


def extract_text_with_layout(data: bytes) -> str:
    if pdfplumber is None:
        return ""
    buffer = io.BytesIO(data)
    texts: List[str] = []
    try:
        with pdfplumber.open(buffer) as pdf:
            for page in pdf.pages:
                try:
                    txt = page.extract_text(layout=True) or page.extract_text() or ""
                except Exception:
                    txt = ""
                if txt:
                    texts.append(txt)
    except Exception:
        return ""
    return "\n".join(texts)
