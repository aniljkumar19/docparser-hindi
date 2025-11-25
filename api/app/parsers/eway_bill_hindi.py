# api/app/parsers/eway_bill_hindi.py
# Hindi parsing rules for e-way bills
import re
from typing import Dict, Any
from datetime import datetime

# Hindi: ई-वे बिल, वे बिल
EWAY_BILL_NO_REGEX_HINDI = re.compile(
    r'(?:ई[-\s]*वे\s*बिल|वे\s*बिल|E[Ww]ay\s*[Bb]ill)\s*(?:संख्या|नंबर|No\.?|Number|#)?\s*[:\-]?\s*([A-Z0-9]{12})',
    re.I | re.UNICODE
)
EWAY_BILL_NO_REGEX = re.compile(r"\bE[Ww]ay\s*[Bb]ill\s*(?:No\.?|Number|#)?\s*[:\-]?\s*([A-Z0-9]{12})\b", re.IGNORECASE)

# Hindi: ई-वे बिल तिथि, वे बिल दिनांक
EWAY_BILL_DATE_REGEX_HINDI = re.compile(
    r'(?:ई[-\s]*वे\s*बिल|वे\s*बिल)?\s*(?:तिथि|दिनांक|Date)\s*[:\-]?\s*([0-9]{2}[-\/\.][0-9]{2}[-\/\.][0-9]{4})',
    re.UNICODE
)
EWAY_BILL_DATE_REGEX = re.compile(r"\b(?:E[Ww]ay\s*[Bb]ill\s*)?[Dd]ate\s*[:\-]?\s*([0-9]{2}[-\/\.][0-9]{2}[-\/\.][0-9]{4})\b")

# Hindi: वैध तक, वैध जब तक
EWAY_BILL_VALID_UNTIL_REGEX_HINDI = re.compile(
    r'(?:वैध\s*तक|वैध\s*जब\s*तक|Valid\s*until|Valid\s*till)\s*[:\-]?\s*([0-9]{2}[-\/\.][0-9]{2}[-\/\.][0-9]{4})',
    re.I | re.UNICODE
)
EWAY_BILL_VALID_UNTIL_REGEX = re.compile(r"\b(?:Valid\s*until|Valid\s*till)\s*[:\-]?\s*([0-9]{2}[-\/\.][0-9]{2}[-\/\.][0-9]{4})\b", re.IGNORECASE)

# Hindi: वाहन संख्या, वाहन नंबर
VEHICLE_NO_REGEX_HINDI = re.compile(
    r'(?:वाहन\s*(?:संख्या|नंबर)|Vehicle\s*No\.?|Veh\.?\s*No\.?)\s*[:\-]?\s*([A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4})',
    re.I | re.UNICODE
)
VEHICLE_NO_REGEX = re.compile(r"\b(?:Vehicle\s*No\.?|Veh\.?\s*No\.?)\s*[:\-]?\s*([A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4})\b", re.IGNORECASE)

# Hindi: परिवहनकर्ता जीएसटीआईएन
TRANSPORTER_GSTIN_REGEX_HINDI = re.compile(
    r'(?:परिवहनकर्ता\s*जीएसटीआईएन|Transporter\s*GSTIN|Trans\s*GSTIN)\s*[:\-]?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])',
    re.I | re.UNICODE
)
TRANSPORTER_GSTIN_REGEX = re.compile(r"\b(?:Transporter\s*GSTIN|Trans\s*GSTIN)\s*[:\-]?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b", re.IGNORECASE)

# Hindi: चालक का नाम
DRIVER_NAME_REGEX_HINDI = re.compile(
    r'(?:चालक\s*(?:का\s*)?नाम|Driver\s*Name|Driver)\s*[:\-]?\s*([A-Za-z\s\u0900-\u097F]+)',
    re.I | re.UNICODE
)
DRIVER_NAME_REGEX = re.compile(r"\b(?:Driver\s*Name|Driver)\s*[:\-]?\s*([A-Za-z\s]+)\b", re.IGNORECASE)

# Hindi: चालक मोबाइल, चालक फोन
DRIVER_MOBILE_REGEX_HINDI = re.compile(
    r'(?:चालक\s*(?:मोबाइल|फोन)|Driver\s*Mobile|Driver\s*Phone)\s*[:\-]?\s*([0-9]{10})',
    re.I | re.UNICODE
)
DRIVER_MOBILE_REGEX = re.compile(r"\b(?:Driver\s*Mobile|Driver\s*Phone)\s*[:\-]?\s*([0-9]{10})\b", re.IGNORECASE)

# Hindi: दूरी
DISTANCE_REGEX_HINDI = re.compile(
    r'(?:दूरी|Distance|Dist)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:किमी|km|kms|kilometers?)',
    re.I | re.UNICODE
)
DISTANCE_REGEX = re.compile(r"\b(?:Distance|Dist)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:km|kms|kilometers?)\b", re.IGNORECASE)

# Hindi: से, मूल स्थान
FROM_PLACE_REGEX_HINDI = re.compile(
    r'(?:से|मूल\s*स्थान|From|Origin)\s*[:\-]?\s*([A-Za-z\s,\u0900-\u097F]+)',
    re.I | re.UNICODE
)
FROM_PLACE_REGEX = re.compile(r"\b(?:From|Origin)\s*[:\-]?\s*([A-Za-z\s,]+)\b", re.IGNORECASE)

# Hindi: तक, गंतव्य
TO_PLACE_REGEX_HINDI = re.compile(
    r'(?:तक|गंतव्य|To|Destination)\s*[:\-]?\s*([A-Za-z\s,\u0900-\u097F]+)',
    re.I | re.UNICODE
)
TO_PLACE_REGEX = re.compile(r"\b(?:To|Destination)\s*[:\-]?\s*([A-Za-z\s,]+)\b", re.IGNORECASE)

# Hindi: चालान संख्या, बिल नंबर
INVOICE_NO_REGEX_HINDI = re.compile(
    r'(?:चालान\s*(?:संख्या|नंबर)|बिल\s*नंबर|Invoice\s*No\.?|Inv\.?)\s*[:\-]?\s*([A-Z0-9\-]+)',
    re.I | re.UNICODE
)
INVOICE_NO_REGEX = re.compile(r"\b(?:Invoice\s*No\.?|Inv\.?)\s*[:\-]?\s*([A-Z0-9\-]+)\b", re.IGNORECASE)

# Hindi: चालान तिथि, बिल दिनांक
INVOICE_DATE_REGEX_HINDI = re.compile(
    r'(?:चालान\s*तिथि|बिल\s*दिनांक|Invoice\s*Date|Inv\s*Date)\s*[:\-]?\s*([0-9]{2}[-\/\.][0-9]{2}[-\/\.][0-9]{4})',
    re.I | re.UNICODE
)
INVOICE_DATE_REGEX = re.compile(r"\b(?:Invoice\s*Date|Inv\s*Date)\s*[:\-]?\s*([0-9]{2}[-\/\.][0-9]{2}[-\/\.][0-9]{4})\b", re.IGNORECASE)

def _to_number(s: str) -> float | None:
    """Convert string to number, handling Indian number formats"""
    try:
        return float(s.replace(",", "").replace("₹", "").replace("$", "").replace("रु", "").replace("रुपये", "").strip())
    except Exception:
        return None

def _normalize_date(date_str: str) -> str | None:
    """Normalize Indian date formats to ISO format"""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    # Try common Indian date formats
    for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y"]:
        try:
            return datetime.strptime(date_str, fmt).date().isoformat()
        except Exception:
            continue
    return date_str

def parse_text_rules_hindi(text: str) -> Dict[str, Any]:
    """Parse Hindi E-way bill text and extract structured data"""
    result = {
        "eway_bill_number": None,
        "eway_bill_date": None,
        "valid_until": None,
        "vehicle_number": None,
        "transporter_gstin": None,
        "driver_name": None,
        "driver_mobile": None,
        "distance": None,
        "from_place": None,
        "to_place": None,
        "invoice_number": None,
        "invoice_date": None,
        "supply_type": None,
        "warnings": []
    }

    # E-way bill number (try Hindi first, then English)
    m = EWAY_BILL_NO_REGEX_HINDI.search(text) or EWAY_BILL_NO_REGEX.search(text)
    if m:
        result["eway_bill_number"] = m.group(1) if m.lastindex >= 1 else None

    # E-way bill date (try Hindi first, then English)
    m = EWAY_BILL_DATE_REGEX_HINDI.search(text) or EWAY_BILL_DATE_REGEX.search(text)
    if m:
        date_str = m.group(1) if m.lastindex >= 1 else None
        result["eway_bill_date"] = _normalize_date(date_str) if date_str else None

    # Valid until (try Hindi first, then English)
    m = EWAY_BILL_VALID_UNTIL_REGEX_HINDI.search(text) or EWAY_BILL_VALID_UNTIL_REGEX.search(text)
    if m:
        date_str = m.group(1) if m.lastindex >= 1 else None
        result["valid_until"] = _normalize_date(date_str) if date_str else None

    # Vehicle number (try Hindi first, then English)
    m = VEHICLE_NO_REGEX_HINDI.search(text) or VEHICLE_NO_REGEX.search(text)
    if m:
        result["vehicle_number"] = m.group(1) if m.lastindex >= 1 else None

    # Transporter GSTIN (try Hindi first, then English)
    m = TRANSPORTER_GSTIN_REGEX_HINDI.search(text) or TRANSPORTER_GSTIN_REGEX.search(text)
    if m:
        result["transporter_gstin"] = m.group(1) if m.lastindex >= 1 else None

    # Driver name (try Hindi first, then English)
    m = DRIVER_NAME_REGEX_HINDI.search(text) or DRIVER_NAME_REGEX.search(text)
    if m:
        result["driver_name"] = (m.group(1) if m.lastindex >= 1 else "").strip()

    # Driver mobile (try Hindi first, then English)
    m = DRIVER_MOBILE_REGEX_HINDI.search(text) or DRIVER_MOBILE_REGEX.search(text)
    if m:
        result["driver_mobile"] = m.group(1) if m.lastindex >= 1 else None

    # Distance (try Hindi first, then English)
    m = DISTANCE_REGEX_HINDI.search(text) or DISTANCE_REGEX.search(text)
    if m:
        result["distance"] = _to_number(m.group(1) if m.lastindex >= 1 else None)

    # From place (try Hindi first, then English)
    m = FROM_PLACE_REGEX_HINDI.search(text) or FROM_PLACE_REGEX.search(text)
    if m:
        result["from_place"] = (m.group(1) if m.lastindex >= 1 else "").strip()

    # To place (try Hindi first, then English)
    m = TO_PLACE_REGEX_HINDI.search(text) or TO_PLACE_REGEX.search(text)
    if m:
        result["to_place"] = (m.group(1) if m.lastindex >= 1 else "").strip()

    # Invoice number (try Hindi first, then English)
    m = INVOICE_NO_REGEX_HINDI.search(text) or INVOICE_NO_REGEX.search(text)
    if m:
        result["invoice_number"] = m.group(1) if m.lastindex >= 1 else None

    # Invoice date (try Hindi first, then English)
    m = INVOICE_DATE_REGEX_HINDI.search(text) or INVOICE_DATE_REGEX.search(text)
    if m:
        date_str = m.group(1) if m.lastindex >= 1 else None
        result["invoice_date"] = _normalize_date(date_str) if date_str else None

    return result

