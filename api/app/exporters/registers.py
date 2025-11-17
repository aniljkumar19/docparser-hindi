import csv
import io
import json
from typing import Any, Dict, List


def export_json(doc: Dict[str, Any]) -> str:
    """Return a pretty-printed JSON string for any parsed document."""
    return json.dumps(doc, indent=2, ensure_ascii=False)


SALES_PURCHASE_CSV_HEADERS = [
    "invoice_date",
    "invoice_number",
    "party_name",
    "party_gstin",
    "place_of_supply",
    "reverse_charge",
    "invoice_type",
    "taxable_value",
    "igst",
    "cgst",
    "sgst",
    "cess",
    "total_value",
]


def _float_or_zero(v: Any) -> float:
    try:
        return float(v or 0.0)
    except (TypeError, ValueError):
        return 0.0


def sales_register_to_csv(sales_register: Dict[str, Any]) -> str:
    """
    Export normalized sales_register JSON to CSV string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(SALES_PURCHASE_CSV_HEADERS)

    for e in sales_register.get("entries", []) or []:
        row = [
            e.get("invoice_date") or "",
            e.get("invoice_number") or "",
            e.get("customer_name") or "",
            e.get("customer_gstin") or "",
            e.get("place_of_supply") or "",
            "Y" if e.get("reverse_charge") else "N",
            e.get("invoice_type") or "REGULAR",
            _float_or_zero(e.get("taxable_value")),
            _float_or_zero(e.get("igst")),
            _float_or_zero(e.get("cgst")),
            _float_or_zero(e.get("sgst")),
            _float_or_zero(e.get("cess")),
            _float_or_zero(e.get("total_value")),
        ]
        writer.writerow(row)

    return output.getvalue()


def purchase_register_to_csv(purchase_register: Dict[str, Any]) -> str:
    """
    Export normalized purchase_register JSON to CSV string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(SALES_PURCHASE_CSV_HEADERS)

    for e in purchase_register.get("entries") or []:
        row = [
            e.get("invoice_number") or "",
            e.get("invoice_date") or "",
            e.get("supplier_name") or "",
            e.get("supplier_gstin") or "",
            e.get("place_of_supply") or "",
            "Y" if e.get("reverse_charge") else "N",
            e.get("invoice_type") or "REGULAR",
            _float_or_zero(e.get("taxable_value")),
            _float_or_zero(e.get("igst")),
            _float_or_zero(e.get("cgst")),
            _float_or_zero(e.get("sgst")),
            _float_or_zero(e.get("cess")),
            _float_or_zero(e.get("total_value")),
        ]
        writer.writerow(row)

    return output.getvalue()


def _infer_gst_rate(entry: Dict[str, Any]) -> float:
    """
    Infer GST % from invoice: (total tax / taxable_value) * 100.
    """
    taxable = _float_or_zero(entry.get("taxable_value"))
    if taxable <= 0:
        return 0.0

    total_tax = (
        _float_or_zero(entry.get("igst"))
        + _float_or_zero(entry.get("cgst"))
        + _float_or_zero(entry.get("sgst"))
        + _float_or_zero(entry.get("cess"))
    )
    rate = (total_tax / taxable) * 100.0
    return round(rate, 2)


def sales_register_to_zoho_invoices(
    sales_register: Dict[str, Any],
    default_item_name: str = "Goods",
) -> List[Dict[str, Any]]:
    """
    Convert normalized sales_register JSON into a list of
    Zoho Books-compatible Sales Invoice payloads.
    """
    invoices: List[Dict[str, Any]] = []

    for e in sales_register.get("entries") or []:
        customer_name = e.get("customer_name") or "Unknown Customer"
        invoice_number = e.get("invoice_number") or ""
        invoice_date = e.get("invoice_date") or ""
        taxable = _float_or_zero(e.get("taxable_value"))
        gst_rate = _infer_gst_rate(e)

        inv = {
            "customer_name": customer_name,
            "reference_number": invoice_number,
            "date": invoice_date,
            "gst_treatment": "business_gst",
            "place_of_supply": e.get("place_of_supply") or "",
            "line_items": [
                {
                    "item_name": default_item_name,
                    "description": default_item_name,
                    "quantity": 1,
                    "rate": taxable,
                    "gst_treatment": "business_gst",
                    "tax_percentage": gst_rate,
                }
            ],
        }

        invoices.append(inv)

    return invoices


def sales_register_to_zoho_json(
    sales_register: Dict[str, Any],
    default_item_name: str = "Goods",
) -> str:
    """
    Wrap sales_register_to_zoho_invoices and return a JSON string.
    """
    payload = {
        "invoices": sales_register_to_zoho_invoices(
            sales_register, default_item_name=default_item_name
        )
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


