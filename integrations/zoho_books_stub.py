# Zoho Books Integration (stub)

"""
Steps:
1) Create a self-client in Zoho Developer Console and obtain a refresh_token.
2) Exchange refresh_token for access_token (OAuth).
3) Use Zoho Books Invoices API to create invoices from parsed JSON.

This stub just shows mapping ideas.
"""

def map_parse_to_zoho_invoice(parse_result: dict) -> dict:
    inv = parse_result
    items = []
    for li in inv.get("line_items", []):
        items.append({
            "name": li.get("desc") or "Item",
            "rate": li.get("unit_price") or 0,
            "quantity": li.get("qty") or 1,
            "item_total": li.get("amount") or 0
        })
    payload = {
        "customer_name": (inv.get("buyer") or {}).get("name") or "Buyer",
        "reference_number": (inv.get("invoice_number") or {}).get("value") or "INV-UNKNOWN",
        "date": (inv.get("date") or {}).get("value") or "2025-01-01",
        "line_items": items,
        "custom_fields": [
            {"label": "GSTIN_Seller", "value": (inv.get("seller") or {}).get("gstin")},
            {"label": "GSTIN_Buyer", "value": (inv.get("buyer") or {}).get("gstin")},
        ],
        "notes": "Imported via Doc Parser API"
    }
    return payload
