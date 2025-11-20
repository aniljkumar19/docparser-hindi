# Canonical Format - Quick Examples

## Side-by-Side Comparison

### Invoice (Before → After)

**Before (Current):**
```json
{
  "invoice_number": "INV-001",
  "date": "2025-01-15",
  "seller": {"name": "ABC Corp", "gstin": "27ABCDE1234F1Z5"},
  "buyer": {"name": "XYZ Ltd", "gstin": "24XYZ9876543Z1B3"},
  "items": [
    {"description": "Product A", "quantity": 10, "unit_price": 10000, "amount": 100000}
  ],
  "tax_breakup": {"cgst": 9000, "sgst": 9000, "igst": 0, "cess": 0},
  "totals": {"subtotal": 100000, "tax_total": 18000, "grand_total": 118000}
}
```

**After (Canonical):**
```json
{
  "schema_version": "doc.v1",
  "doc_type": "invoice",
  "doc_id": "inv-2025-001",
  "doc_date": "2025-01-15",
  "business": {"name": "ABC Corp", "gstin": "27ABCDE1234F1Z5"},
  "parties": {
    "primary": {"name": "ABC Corp", "gstin": "27ABCDE1234F1Z5"},
    "counterparty": {"name": "XYZ Ltd", "gstin": "24XYZ9876543Z1B3"}
  },
  "financials": {
    "currency": "INR",
    "subtotal": 100000.00,
    "tax_breakup": {"cgst": 9000.00, "sgst": 9000.00, "igst": 0.00, "cess": 0.00},
    "tax_total": 18000.00,
    "grand_total": 118000.00
  },
  "entries": [{
    "entry_id": "main-invoice",
    "entry_type": "invoice",
    "entry_date": "2025-01-15",
    "entry_number": "INV-001",
    "line_items": [
      {"description": "Product A", "quantity": 10, "unit_price": 10000, "amount": 100000}
    ],
    "amounts": {"taxable_value": 100000.00, "total": 118000.00}
  }]
}
```

### Purchase Register (Before → After)

**Before (Current):**
```json
{
  "doc_type": "purchase_register",
  "gstin_of_business": "27ABCDE1234F1Z5",
  "period": "2025-01",
  "entries": [
    {
      "invoice_number": "PUR-001",
      "invoice_date": "2025-01-05",
      "supplier_name": "XYZ Distributors",
      "supplier_gstin": "27XYZ9876543Z1B3",
      "taxable_value": 100000.00,
      "cgst": 9000.00,
      "sgst": 9000.00,
      "total_value": 118000.00
    }
  ]
}
```

**After (Canonical):**
```json
{
  "schema_version": "doc.v1",
  "doc_type": "purchase_register",
  "doc_id": "purchase-reg-2025-01",
  "period": "2025-01",
  "business": {"name": "Company Name", "gstin": "27ABCDE1234F1Z5", "state_code": "27"},
  "financials": {
    "currency": "INR",
    "subtotal": 100000.00,
    "tax_breakup": {"cgst": 9000.00, "sgst": 9000.00, "igst": 0.00},
    "tax_total": 18000.00,
    "grand_total": 118000.00
  },
  "entries": [{
    "entry_id": "entry-1",
    "entry_type": "register_entry",
    "entry_date": "2025-01-05",
    "entry_number": "PUR-001",
    "party": {
      "name": "XYZ Distributors",
      "gstin": "27XYZ9876543Z1B3",
      "state_code": "27"
    },
    "amounts": {
      "taxable_value": 100000.00,
      "tax_breakup": {"cgst": 9000.00, "sgst": 9000.00, "igst": 0.00},
      "total": 118000.00
    },
    "doc_specific": {
      "reverse_charge": false,
      "invoice_type": "REGULAR"
    }
  }]
}
```

## Key Changes Summary

| Aspect | Current | Canonical |
|--------|---------|-----------|
| **Top-level structure** | Varies by doc type | Always: `schema_version`, `doc_type`, `doc_id`, `doc_date`, `metadata`, `business`, `parties`, `financials`, `entries` |
| **Party fields** | `seller`/`buyer`, `supplier_name`/`customer_name` | Always `parties.primary` and `parties.counterparty` |
| **Financial fields** | `totals`, `tax_breakup` (varies) | Always `financials` with consistent structure |
| **Items/Entries** | `items`, `entries`, `transactions` | Always `entries[]` array |
| **Tax structure** | Varies (sometimes flat, sometimes nested) | Always `tax_breakup` object with `cgst`, `sgst`, `igst`, `cess` |
| **Document-specific** | Mixed with common fields | Isolated in `doc_specific` section |

## Benefits

1. **Single Integration Path**: Clients learn one format for all document types
2. **Consistent Field Names**: `parties.primary` always means the same thing
3. **Predictable Structure**: Always know where to find financials, parties, entries
4. **Easier Validation**: One JSON schema validates all document types
5. **Simpler Exporters**: Tally/Zoho exporters work with one format

## Migration Path

```python
# Step 1: Add canonical normalizer
def normalize_to_canonical(doc_type: str, parsed_data: dict) -> dict:
    if doc_type == "invoice":
        return normalize_invoice_to_canonical(parsed_data)
    elif doc_type == "purchase_register":
        return normalize_purchase_register_to_canonical(parsed_data)
    # ... etc

# Step 2: Update API endpoint
@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str, format: str = "legacy"):
    job = get_job_by_id(db, job_id)
    result = json.loads(job.result)
    
    if format == "canonical":
        canonical = normalize_to_canonical(job.doc_type, result)
        return {"result": canonical, "format": "canonical"}
    else:
        return {"result": result, "format": "legacy"}
```

