import os, time
import stripe

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY","")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID","")
stripe.api_key = STRIPE_API_KEY

SUBS_ITEMS_MAP = {}
_map = os.getenv("STRIPE_SUBSCRIPTION_ITEMS","")
for pair in _map.split(","):
    pair = pair.strip()
    if not pair or ":" not in pair:
        continue
    k, v = pair.split(":", 1)
    SUBS_ITEMS_MAP[k.strip()] = v.strip()

def record_usage(api_key: str, qty: int = 1, timestamp: int = None):
    if not STRIPE_API_KEY:
        return {"ok": False, "skipped": True, "reason": "No STRIPE_API_KEY"}
    sub_item = SUBS_ITEMS_MAP.get(api_key)
    if not sub_item:
        return {"ok": False, "skipped": True, "reason": "No subscription_item_id for API key"}
    ts = timestamp or int(time.time())
    try:
        usage_record = stripe.UsageRecord.create(quantity=qty, timestamp=ts, action="increment", subscription_item=sub_item)
        return {"ok": True, "id": usage_record.id}
    except Exception as e:
        return {"ok": False, "error": str(e)}
