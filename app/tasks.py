# app/tasks.py (RESCUE VERSION)

import time
import json

# use your existing repo helpers; they should already exist
from .repo import update_job_result, inc_usage, get_webhook
# if you prefer, comment out webhooks for now to avoid extra deps
# import requests  # (leave out in rescue)

def process_job(db_factory, job_id: str, api_key: str, filename: str, storage_uri: str):
    t0 = time.time()
    try:
        # Minimal canonical payload so clients see a stable shape
        result = {
            "schema_version": "invoice.v0",
            "doc_type": "invoice",
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "seller": None,
            "buyer": None,
            "place_of_supply": None,
            "items": [],
            "tax_breakup": {"cgst": 0.0, "sgst": 0.0, "igst": 0.0, "cess": 0.0},
            "totals": {"subtotal": 0.0, "tax_total": 0.0, "grand_total": 0.0, "currency": "INR"},
            "notes": None,
            "po_number": None,
            "meta": {"source_file": filename},
        }

        meta = {
            "pages": 1,
            "ocr_used": False,
            "processing_ms": int((time.time() - t0) * 1000),
            "schema_version": result["schema_version"],
        }

        with db_factory() as db:
            update_job_result(db, job_id, "succeeded", meta, result)
            inc_usage(db, api_key, 1)

            wb = get_webhook(db, api_key)
            if wb and getattr(wb, "url", None):
                # keep webhook minimal; or comment this whole block out in rescue
                pass
                # try:
                #     requests.post(wb.url, json={
                #         "job_id": job_id,
                #         "status": "succeeded",
                #         "doc_type": result["doc_type"],
                #         "result": result,
                #         "meta": meta,
                #     }, timeout=2)
                # except Exception:
                #     pass

    except Exception as e:
        with db_factory() as db:
            update_job_result(db, job_id, "failed", {"error": str(e)}, None)
