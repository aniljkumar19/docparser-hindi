"""
Base utilities for canonical format normalizers.
Shared helper functions used by all normalizers.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def _extract_value(field: Any) -> Optional[str]:
    """Extract value from field that might be dict with 'value' key or direct value."""
    if field is None:
        return None
    if isinstance(field, dict):
        return field.get("value")
    return str(field) if field else None


def _extract_address(party: Dict[str, Any]) -> Dict[str, Any]:
    """Extract address from party dict."""
    if not isinstance(party, dict):
        return {}
    address = party.get("address") or {}
    if isinstance(address, str):
        return {"raw": address}
    return address if isinstance(address, dict) else {}


def _extract_state_code(gstin: Optional[str]) -> Optional[str]:
    """Extract state code from GSTIN (first 2 digits)."""
    if not gstin:
        return None
    gstin_str = str(gstin).strip()
    if len(gstin_str) >= 2:
        return gstin_str[:2]
    return None


def _normalize_date(date_str: Any) -> Optional[str]:
    """Normalize date to YYYY-MM-DD format."""
    if not date_str:
        return None
    
    date_val = _extract_value(date_str) if isinstance(date_str, dict) else str(date_str)
    if not date_val:
        return None
    
    # If already in YYYY-MM-DD format, return as-is
    if isinstance(date_val, str) and len(date_val) >= 10:
        if date_val[4] == "-" and date_val[7] == "-":
            return date_val[:10]
    
    # Try parsing common formats
    formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y",
        "%m-%d-%Y", "%m/%d/%Y", "%d-%m-%y", "%d/%m/%y",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_val[:10], fmt)
            return dt.strftime("%Y-%m-%d")
        except:
            continue
    
    return date_val[:10] if len(date_val) >= 10 else date_val


def _to_float(value: Any) -> float:
    """Convert value to float, defaulting to 0.0."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove currency symbols and commas
        cleaned = value.replace("₹", "").replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except:
            return 0.0
    return 0.0


def _build_tax_breakup_from_taxes(taxes: List[Dict[str, Any]]) -> Dict[str, float]:
    """Build tax_breakup dict from taxes array."""
    breakup = {
        "cgst": 0.0,
        "sgst": 0.0,
        "igst": 0.0,
        "cess": 0.0,
        "tds": 0.0,
        "tcs": 0.0,
    }
    
    for tax in taxes:
        if not isinstance(tax, dict):
            continue
        tax_type = str(tax.get("type", "")).upper()
        amount = _to_float(tax.get("amount") or tax.get("rate"))
        
        if "CGST" in tax_type:
            breakup["cgst"] += amount
        elif "SGST" in tax_type:
            breakup["sgst"] += amount
        elif "IGST" in tax_type:
            breakup["igst"] += amount
        elif "CESS" in tax_type:
            breakup["cess"] += amount
        elif "TDS" in tax_type:
            breakup["tds"] += amount
        elif "TCS" in tax_type:
            breakup["tcs"] += amount
    
    return breakup


def _generate_doc_id(doc_type: str, identifier: Optional[str]) -> str:
    """Generate a unique document ID."""
    if identifier:
        # Clean identifier for use in doc_id
        clean_id = str(identifier).lower().replace(" ", "-").replace("/", "-")
        return f"{doc_type}-{clean_id}"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{doc_type}-{timestamp}".lower()

