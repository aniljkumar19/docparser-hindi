import requests

class ZohoBooksClient:
    def __init__(self, org_id: str, access_token: str):
        self.org_id = org_id
        self.access_token = access_token
        self.base = "https://books.zoho.com/api/v3"

    def _headers(self):
        return {"Authorization": f"Zoho-oauthtoken {self.access_token}", "Content-Type": "application/json"}

    def create_invoice(self, payload: dict):
        url = f"{self.base}/invoices?organization_id={self.org_id}"
        r = requests.post(url, json=payload, headers=self._headers(), timeout=20)
        return r.status_code, r.json()

def map_parsed_to_zoho_invoice(parsed: dict) -> dict:
    line_items = []
    for li in parsed.get("line_items", []):
        line_items.append({"item_name": li.get("desc","Item"), "quantity": li.get("qty",1), "rate": li.get("unit_price",0)})
    customer_name = (parsed.get("buyer") or {}).get("name") or "Customer"
    inv_no = (parsed.get("invoice_number") or {}).get("value") if isinstance(parsed.get("invoice_number"), dict) else parsed.get("invoice_number")
    date = (parsed.get("date") or {}).get("value") if isinstance(parsed.get("date"), dict) else parsed.get("date")
    return {"customer_name": customer_name, "reference_number": inv_no, "date": date, "line_items": line_items}
