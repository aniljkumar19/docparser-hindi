import re
from typing import Dict, Any, List

# E-way bill specific patterns for Indian market
EWAY_BILL_NO_REGEX = re.compile(r"\bE[Ww]ay\s*[Bb]ill\s*(?:No\.?|Number|#)?\s*[:\-]?\s*([A-Z0-9]{12})\b", re.IGNORECASE)
EWAY_BILL_DATE_REGEX = re.compile(r"\b(?:E[Ww]ay\s*[Bb]ill\s*)?[Dd]ate\s*[:\-]?\s*([0-9]{2}[-\/\.][0-9]{2}[-\/\.][0-9]{4})\b")
EWAY_BILL_VALID_UNTIL_REGEX = re.compile(r"\b(?:Valid\s*until|Valid\s*till)\s*[:\-]?\s*([0-9]{2}[-\/\.][0-9]{2}[-\/\.][0-9]{4})\b", re.IGNORECASE)

# Vehicle and transport details
VEHICLE_NO_REGEX = re.compile(r"\b(?:Vehicle\s*No\.?|Veh\.?\s*No\.?)\s*[:\-]?\s*([A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4})\b", re.IGNORECASE)
TRANSPORTER_GSTIN_REGEX = re.compile(r"\b(?:Transporter\s*GSTIN|Trans\s*GSTIN)\s*[:\-]?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b", re.IGNORECASE)
DRIVER_NAME_REGEX = re.compile(r"\b(?:Driver\s*Name|Driver)\s*[:\-]?\s*([A-Za-z\s]+)\b", re.IGNORECASE)
DRIVER_MOBILE_REGEX = re.compile(r"\b(?:Driver\s*Mobile|Driver\s*Phone)\s*[:\-]?\s*([0-9]{10})\b", re.IGNORECASE)

# Distance and route details
DISTANCE_REGEX = re.compile(r"\b(?:Distance|Dist)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:km|kms|kilometers?)\b", re.IGNORECASE)
FROM_PLACE_REGEX = re.compile(r"\b(?:From|Origin)\s*[:\-]?\s*([A-Za-z\s,]+)\b", re.IGNORECASE)
TO_PLACE_REGEX = re.compile(r"\b(?:To|Destination)\s*[:\-]?\s*([A-Za-z\s,]+)\b", re.IGNORECASE)

# Document references
INVOICE_NO_REGEX = re.compile(r"\b(?:Invoice\s*No\.?|Inv\.?)\s*[:\-]?\s*([A-Z0-9\-]+)\b", re.IGNORECASE)
INVOICE_DATE_REGEX = re.compile(r"\b(?:Invoice\s*Date|Inv\s*Date)\s*[:\-]?\s*([0-9]{2}[-\/\.][0-9]{2}[-\/\.][0-9]{4})\b", re.IGNORECASE)

# Supply type patterns
SUPPLY_TYPE_REGEX = re.compile(r"\b(?:Supply\s*Type|Type\s*of\s*Supply)\s*[:\-]?\s*(Regular|Outward|Inward|Import|Export)\b", re.IGNORECASE)

def _to_number(s: str) -> float | None:
    """Convert string to number, handling Indian number formats"""
    try:
        return float(s.replace(",", "").replace("₹", "").replace("$", "").strip())
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
            from datetime import datetime
            return datetime.strptime(date_str, fmt).date().isoformat()
        except Exception:
            continue
    return date_str

def parse_text_rules(text: str) -> Dict[str, Any]:
    """Parse E-way bill text and extract structured data"""
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
        "seller": {},
        "buyer": {},
        "line_items": [],
        "warnings": []
    }
    
    # Extract E-way bill number
    eway_match = EWAY_BILL_NO_REGEX.search(text)
    if eway_match:
        result["eway_bill_number"] = {"value": eway_match.group(1), "confidence": 0.9}
    
    # Extract dates
    date_match = EWAY_BILL_DATE_REGEX.search(text)
    if date_match:
        result["eway_bill_date"] = {"value": _normalize_date(date_match.group(1)), "confidence": 0.8}
    
    valid_match = EWAY_BILL_VALID_UNTIL_REGEX.search(text)
    if valid_match:
        result["valid_until"] = {"value": _normalize_date(valid_match.group(1)), "confidence": 0.8}
    
    # Extract vehicle details
    vehicle_match = VEHICLE_NO_REGEX.search(text)
    if vehicle_match:
        result["vehicle_number"] = {"value": vehicle_match.group(1), "confidence": 0.9}
    
    transporter_match = TRANSPORTER_GSTIN_REGEX.search(text)
    if transporter_match:
        result["transporter_gstin"] = {"value": transporter_match.group(1), "confidence": 0.9}
    
    driver_name_match = DRIVER_NAME_REGEX.search(text)
    if driver_name_match:
        result["driver_name"] = {"value": driver_name_match.group(1).strip(), "confidence": 0.8}
    
    driver_mobile_match = DRIVER_MOBILE_REGEX.search(text)
    if driver_mobile_match:
        result["driver_mobile"] = {"value": driver_mobile_match.group(1), "confidence": 0.9}
    
    # Extract route details
    distance_match = DISTANCE_REGEX.search(text)
    if distance_match:
        result["distance"] = {"value": _to_number(distance_match.group(1)), "confidence": 0.8}
    
    from_match = FROM_PLACE_REGEX.search(text)
    if from_match:
        result["from_place"] = {"value": from_match.group(1).strip(), "confidence": 0.8}
    
    to_match = TO_PLACE_REGEX.search(text)
    if to_match:
        result["to_place"] = {"value": to_match.group(1).strip(), "confidence": 0.8}
    
    # Extract invoice references
    inv_no_match = INVOICE_NO_REGEX.search(text)
    if inv_no_match:
        result["invoice_number"] = {"value": inv_no_match.group(1), "confidence": 0.9}
    
    inv_date_match = INVOICE_DATE_REGEX.search(text)
    if inv_date_match:
        result["invoice_date"] = {"value": _normalize_date(inv_date_match.group(1)), "confidence": 0.8}
    
    # Extract supply type
    supply_match = SUPPLY_TYPE_REGEX.search(text)
    if supply_match:
        result["supply_type"] = {"value": supply_match.group(1), "confidence": 0.8}
    
    # Extract GSTINs for seller/buyer
    from .rules import GSTIN_REGEX
    gstins = GSTIN_REGEX.findall(text)
    if gstins:
        result["seller"] = {"gstin": gstins[0]}
        if len(gstins) > 1:
            result["buyer"] = {"gstin": gstins[1]}
    
    return result

