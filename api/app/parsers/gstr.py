import re
from typing import Dict, Any, List
from datetime import datetime

# GSTR form patterns for Indian GST returns
GSTR_FORM_REGEX = re.compile(r"\bGSTR[-\s]?([1-9][A-Z]?)\b", re.IGNORECASE)
GSTR_PERIOD_REGEX = re.compile(r"\b(?:Period|Month|Year)\s*[:\-]?\s*([0-9]{2}[-\/\.][0-9]{4}|[A-Z]{3}[-\/\.][0-9]{4})\b", re.IGNORECASE)

# GSTIN and business details
GSTIN_REGEX = re.compile(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b")
BUSINESS_NAME_REGEX = re.compile(r"\b(?:Business\s*Name|Legal\s*Name|Company\s*Name)\s*[:\-]?\s*([A-Za-z\s&.,]+)\b", re.IGNORECASE)

# Turnover and tax details
TURNOVER_REGEX = re.compile(r"\b(?:Turnover|Sales|Revenue)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)
TAXABLE_VALUE_REGEX = re.compile(r"\b(?:Taxable\s*Value|Taxable\s*Amount)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)
IGST_REGEX = re.compile(r"\bIGST\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)
CGST_REGEX = re.compile(r"\bCGST\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)
SGST_REGEX = re.compile(r"\bSGST\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)
CESS_REGEX = re.compile(r"\bCESS\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)

# HSN/SAC classification
HSN_REGEX = re.compile(r"\bHSN\s*[:\-]?\s*([0-9]{4,8})\b", re.IGNORECASE)
SAC_REGEX = re.compile(r"\bSAC\s*[:\-]?\s*([0-9]{4,8})\b", re.IGNORECASE)

# Invoice details for GSTR-1
INVOICE_NO_REGEX = re.compile(r"\b(?:Invoice\s*No\.?|Inv\.?)\s*[:\-]?\s*([A-Z0-9\-]+)\b", re.IGNORECASE)
INVOICE_DATE_REGEX = re.compile(r"\b(?:Invoice\s*Date|Inv\s*Date)\s*[:\-]?\s*([0-9]{2}[-\/\.][0-9]{2}[-\/\.][0-9]{4})\b", re.IGNORECASE)
INVOICE_VALUE_REGEX = re.compile(r"\b(?:Invoice\s*Value|Inv\s*Value)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)

# Customer/Supplier details
CUSTOMER_GSTIN_REGEX = re.compile(r"\b(?:Customer\s*GSTIN|Buyer\s*GSTIN)\s*[:\-]?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b", re.IGNORECASE)
SUPPLIER_GSTIN_REGEX = re.compile(r"\b(?:Supplier\s*GSTIN|Vendor\s*GSTIN)\s*[:\-]?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b", re.IGNORECASE)

# Place of supply
PLACE_OF_SUPPLY_REGEX = re.compile(r"\b(?:Place\s*of\s*Supply|POS)\s*[:\-]?\s*([0-9]{2})\b", re.IGNORECASE)

# Reverse charge mechanism
REVERSE_CHARGE_REGEX = re.compile(r"\b(?:Reverse\s*Charge|RCM)\s*[:\-]?\s*(Yes|No|Y|N)\b", re.IGNORECASE)

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
            return datetime.strptime(date_str, fmt).date().isoformat()
        except Exception:
            continue
    return date_str

def _normalize_period(period_str: str) -> str | None:
    """Normalize GSTR period format"""
    if not period_str:
        return None
    
    period_str = period_str.strip()
    # Handle formats like "03-2024", "Mar-2024", "032024"
    if re.match(r"^[0-9]{2}[-\/\.][0-9]{4}$", period_str):
        return period_str.replace("/", "-").replace(".", "-")
    elif re.match(r"^[A-Z]{3}[-\/\.][0-9]{4}$", period_str):
        return period_str.replace("/", "-").replace(".", "-")
    return period_str

def parse_text_rules(text: str) -> Dict[str, Any]:
    """Parse GSTR form text and extract structured data"""
    result = {
        "gstr_form": None,
        "period": None,
        "business_name": None,
        "gstin": None,
        "turnover": None,
        "taxable_value": None,
        "taxes": [],
        "invoices": [],
        "customers": [],
        "suppliers": [],
        "hsn_codes": [],
        "sac_codes": [],
        "place_of_supply": None,
        "reverse_charge": None,
        "warnings": []
    }
    
    # Extract GSTR form type
    form_match = GSTR_FORM_REGEX.search(text)
    if form_match:
        result["gstr_form"] = {"value": f"GSTR-{form_match.group(1)}", "confidence": 0.9}
    
    # Extract period
    period_match = GSTR_PERIOD_REGEX.search(text)
    if period_match:
        result["period"] = {"value": _normalize_period(period_match.group(1)), "confidence": 0.8}
    
    # Extract business details
    business_match = BUSINESS_NAME_REGEX.search(text)
    if business_match:
        result["business_name"] = {"value": business_match.group(1).strip(), "confidence": 0.8}
    
    # Extract GSTIN
    gstin_match = GSTIN_REGEX.search(text)
    if gstin_match:
        result["gstin"] = {"value": gstin_match.group(1), "confidence": 0.9}
    
    # Extract financial details
    turnover_match = TURNOVER_REGEX.search(text)
    if turnover_match:
        result["turnover"] = {"value": _to_number(turnover_match.group(1)), "confidence": 0.8}
    
    taxable_match = TAXABLE_VALUE_REGEX.search(text)
    if taxable_match:
        result["taxable_value"] = {"value": _to_number(taxable_match.group(1)), "confidence": 0.8}
    
    # Extract tax details
    tax_patterns = [
        (IGST_REGEX, "IGST"), (CGST_REGEX, "CGST"), 
        (SGST_REGEX, "SGST"), (CESS_REGEX, "CESS")
    ]
    
    for pattern, tax_type in tax_patterns:
        for match in pattern.finditer(text):
            amount = _to_number(match.group(1))
            if amount:
                result["taxes"].append({
                    "type": tax_type,
                    "amount": amount,
                    "confidence": 0.8
                })
    
    # Extract invoice details
    invoice_nos = INVOICE_NO_REGEX.findall(text)
    invoice_dates = INVOICE_DATE_REGEX.findall(text)
    invoice_values = INVOICE_VALUE_REGEX.findall(text)
    
    for i, inv_no in enumerate(invoice_nos):
        invoice = {"invoice_number": inv_no}
        if i < len(invoice_dates):
            invoice["date"] = _normalize_date(invoice_dates[i])
        if i < len(invoice_values):
            invoice["value"] = _to_number(invoice_values[i])
        result["invoices"].append(invoice)
    
    # Extract customer/supplier GSTINs
    customer_gstins = CUSTOMER_GSTIN_REGEX.findall(text)
    supplier_gstins = SUPPLIER_GSTIN_REGEX.findall(text)
    
    for gstin in customer_gstins:
        result["customers"].append({"gstin": gstin})
    
    for gstin in supplier_gstins:
        result["suppliers"].append({"gstin": gstin})
    
    # Extract HSN/SAC codes
    hsn_codes = HSN_REGEX.findall(text)
    sac_codes = SAC_REGEX.findall(text)
    
    if hsn_codes:
        result["hsn_codes"] = hsn_codes
    if sac_codes:
        result["sac_codes"] = sac_codes
    
    # Extract place of supply
    pos_match = PLACE_OF_SUPPLY_REGEX.search(text)
    if pos_match:
        result["place_of_supply"] = {"value": pos_match.group(1), "confidence": 0.8}
    
    # Extract reverse charge
    rcm_match = REVERSE_CHARGE_REGEX.search(text)
    if rcm_match:
        result["reverse_charge"] = {"value": rcm_match.group(1).upper(), "confidence": 0.8}
    
    result["invoices"] = _clean_invoice_entries(result.get("invoices") or [])
    return result


def _clean_invoice_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    seen = set()
    for entry in entries or []:
        num = (entry.get("invoice_number") or "").strip()
        if len(num) < 4:
            continue
        if num.lower().endswith("voice") and num.lower() != "invoice":
            num = num[-6:]
        if not num or num.lower() == "invoice":
            continue
        if num in seen:
            continue
        seen.add(num)
        cleaned_entry = dict(entry)
        cleaned_entry["invoice_number"] = num
        cleaned.append(cleaned_entry)
    return cleaned


def gstr_quality_score(parsed: Dict[str, Any]) -> int:
    score = 0
    if parsed.get("gstr_form"):
        score += 2
    if parsed.get("period"):
        score += 2
    if parsed.get("turnover"):
        score += 1
    if parsed.get("taxable_value"):
        score += 1
    taxes = parsed.get("taxes") or []
    score += min(2, len(taxes))
    invoices = parsed.get("invoices") or []
    score += min(2, len(invoices))
    return score

