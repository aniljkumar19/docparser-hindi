#!/usr/bin/env python3
import os, sys, stripe, psycopg2

"""
Creates or reuses:
- Product:   "Doc Parser"
- Prices:    Base (recurring)  $49/mo,  lookup_key=docparser_base_v1
             Metered per unit  $0.02    lookup_key=docparser_metered_v1 (usage_type=metered)
- Customer + Subscription (both prices)
- Saves IDs into tenants table.

Usage:
  STRIPE_API_KEY=sk_test_xxx python scripts/bootstrap_stripe_tenant.py tenant_acme "Acme Inc" ops@acme.com
"""

BASE_LOOKUP   = "docparser_base_v1"
METERED_LOOKUP= "docparser_metered_v1"
PRODUCT_NAME  = "Doc Parser"


def get_env(name: str, default: str | None = None, required: bool = False) -> str | None:
    v = os.getenv(name, default)
    if required and not v:
        print(f"Missing env {name}", file=sys.stderr)
        sys.exit(2)
    return v

# near the top of scripts/bootstrap_stripe_tenant.py
def assert_key_matches_mode(db_url: str, api_key: str):
    is_live = api_key.startswith("sk_live_")
    if "localhost" in db_url or "127.0.0.1" in db_url:
        # probably dev/staging: prefer sk_test
        if is_live:
            raise SystemExit("Refusing to use LIVE key with a local/staging DB.")
    else:
        # probably prod: prefer sk_live
        if not is_live:
            raise SystemExit("Refusing to use TEST key with a production DB.")


def get_env(name, default=None, required=False):
    v = os.getenv(name, default)
    if required and not v:
        print(f"Missing env {name}", file=sys.stderr); sys.exit(2)
    return v

def get_or_create_product():
    prods = stripe.Product.search(query=f'name:\'{PRODUCT_NAME}\'', limit=1)
    if prods.data:
        return prods.data[0]
    return stripe.Product.create(name=PRODUCT_NAME)

def get_or_create_price(lookup_key, unit_amount, currency, recurring, **kw):
    # try to find by lookup_key
    prices = stripe.Price.list(lookup_keys=[lookup_key], expand=['data.product'], limit=1)
    if prices.data:
        return prices.data[0]
    return stripe.Price.create(
        lookup_key=lookup_key,
        unit_amount=unit_amount,  # in cents
        currency=currency,
        recurring=recurring,
        product=get_or_create_product().id,
        **kw
    )

def main():
    # in main():
    db_url = get_env("DB_URL", "postgresql://docuser:docpass@localhost:5432/docdb")
    stripe.api_key = get_env("STRIPE_API_KEY", required=True)
    #assert_key_matches_mode(db_url, stripe.api_key)

    if len(sys.argv) < 4:
        print("Usage: python scripts/bootstrap_stripe_tenant.py <tenant_id> <tenant_name> <email>", file=sys.stderr)
        sys.exit(1)
    tenant_id, tenant_name, email = sys.argv[1:4]

    stripe.api_key = get_env("STRIPE_API_KEY", required=True)

    # 1) Ensure prices exist
    base = get_or_create_price(
        BASE_LOOKUP, unit_amount=4900, currency="usd",
        recurring={"interval":"month"}
    )
    metered = get_or_create_price(
        METERED_LOOKUP, unit_amount=2, currency="usd",   # $0.02
        recurring={"interval":"month", "usage_type":"metered", "aggregate_usage":"sum"}
    )

    # 2) Customer + Subscription (base + metered)
    customer = stripe.Customer.create(name=tenant_name, email=email)
    # --- ADD THIS: attach a test payment method in test mode ---
    # (pm_card_visa is a built-in test PaymentMethod ID; only works with sk_test_ keys)
    USE_TEST_PM = os.getenv("USE_TEST_PM", "1") == "1"
    if USE_TEST_PM:
        pm = stripe.PaymentMethod.attach("pm_card_visa", customer=customer.id)
        stripe.Customer.modify(customer.id, invoice_settings={"default_payment_method": pm.id})

    # Optional: give a trial to avoid immediate charge (even in test)
    TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "0") or 0)

    # Choose how Stripe should collect payment
    BILLING_MODE = os.getenv("BILLING_MODE", "charge_automatically")  # or "invoice"

    sub_kwargs = {
        "customer": customer.id,
        "items": [
            {"price": base.id},        # base recurring
            {"price": metered.id},     # metered usage
        ],
        "expand": ["items.data.price"],
    }
    if TRIAL_DAYS > 0:
        sub_kwargs["trial_period_days"] = TRIAL_DAYS

    if BILLING_MODE == "invoice":
        # Do NOT require a card; Stripe sends an invoice email instead
        sub_kwargs.update({
            "collection_method": "send_invoice",
            "days_until_due": 30,
            "payment_behavior": "allow_incomplete",
        })
    else:
        # charge_automatically (default). With pm_card_visa attached, this will succeed.
        sub_kwargs.update({
            "payment_behavior": "default_incomplete",  # safe default, will confirm immediately with default PM
        })

    sub = stripe.Subscription.create(**sub_kwargs)

    # find the metered item on the subscription
    metered_item_id = None
    for it in sub["items"]["data"]:
        price = it["price"]
        if (price.get("lookup_key") == METERED_LOOKUP) or (price.get("recurring",{}).get("usage_type") == "metered"):
            metered_item_id = it["id"]; break
    if not metered_item_id:
        print("ERROR: could not find metered subscription item", file=sys.stderr)
        sys.exit(3)

    # 3) Save to Postgres
    db_url = get_env("DB_URL", "postgresql://docuser:docpass@localhost:5432/docdb")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tenants (id, name, contact_email, stripe_customer_id, stripe_subscription_id, stripe_item_parse)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO UPDATE
        SET name=EXCLUDED.name,
            contact_email=EXCLUDED.contact_email,
            stripe_customer_id=EXCLUDED.stripe_customer_id,
            stripe_subscription_id=EXCLUDED.stripe_subscription_id,
            stripe_item_parse=EXCLUDED.stripe_item_parse
    """, (tenant_id, tenant_name, email, customer.id, sub.id, metered_item_id))
    cur.close(); conn.close()

    print("OK")
    print("tenant_id:", tenant_id)
    print("stripe_customer_id:", customer.id)
    print("stripe_subscription_id:", sub.id)
    print("stripe_item_parse:", metered_item_id)

if __name__ == "__main__":
    main()
