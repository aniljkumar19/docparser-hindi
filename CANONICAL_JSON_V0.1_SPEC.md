# Canonical JSON Format v0.1 - Specification

## Overview

Canonical JSON v0.1 is a unified document format that works for all document types (invoices, registers, GSTR, bank statements, etc.). It provides a consistent structure while allowing document-specific fields.

## Top-Level Structure

```json
{
  "schema_version": "doc.v0.1",
  "doc_type": "invoice|purchase_register|sales_register|gstr3b|gstr1|bank_statement|...",
  "doc_id": "unique-document-identifier",
  "doc_date": "YYYY-MM-DD" | null,
  "period": "YYYY-MM" | null,
  "metadata": {...},
  "business": {...},
  "parties": {...},
  "financials": {...},
  "entries": [...],
  "doc_specific": {...}
}
```

## Field Definitions

### `schema_version` (string, required)
- Always `"doc.v0.1"` for this version
- Used for format versioning

### `doc_type` (string, required)
- Document type identifier
- Examples: `"invoice"`, `"purchase_register"`, `"sales_register"`, `"gstr3b"`, `"gstr1"`, `"bank_statement"`

### `doc_id` (string, required)
- Unique identifier for this document
- Format: `"{doc_type}-{identifier}"`
- Examples: `"invoice-INV-001"`, `"purchase_register-2025-01"`

### `doc_date` (string | null)
- Primary date of the document (ISO format: `YYYY-MM-DD`)
- `null` for period-based documents (registers, GSTR)

### `period` (string | null)
- Period for period-based documents (ISO format: `YYYY-MM`)
- `null` for single-date documents (invoices)

### `metadata` (object, required)
```json
{
  "source_format": "invoice|purchase_register|...",
  "parser_version": "parser_v1",
  "warnings": ["warning1", "warning2"],
  "processing_timestamp": "2025-01-15T10:30:00Z"  // optional
}
```

### `business` (object, required)
Business entity that owns/created this document.

```json
{
  "name": "Company Name" | null,
  "gstin": "27ABCDE1234F1Z5" | null,
  "address": {} | null,
  "state_code": "27" | null  // First 2 digits of GSTIN
}
```

### `parties` (object, required)
Parties involved in the document.

```json
{
  "primary": {
    "name": "Seller/Company Name" | null,
    "gstin": "27ABCDE1234F1Z5" | null,
    "address": {} | null,
    "state_code": "27" | null
  },
  "counterparty": {  // Optional, only for documents with two parties
    "name": "Buyer/Supplier/Customer Name" | null,
    "gstin": "24XYZ9876543Z1B3" | null,
    "address": {} | null,
    "state_code": "24" | null
  }
}
```

**Notes:**
- For invoices: `primary` = seller, `counterparty` = buyer
- For purchase registers: `primary` = company, `counterparty` = supplier (per entry)
- For sales registers: `primary` = company, `counterparty` = customer (per entry)
- For GSTR: `primary` = business filing the return

### `financials` (object, required)
Aggregated financial summary for the entire document.

```json
{
  "currency": "INR" | "USD" | ...,
  "subtotal": 100000.00,
  "tax_breakup": {
    "cgst": 9000.00,
    "sgst": 9000.00,
    "igst": 0.00,
    "cess": 0.00,
    "tds": 0.00,
    "tcs": 0.00
  },
  "tax_total": 18000.00,
  "grand_total": 118000.00,
  "round_off": 0.00
}
```

**Notes:**
- `subtotal`: Base amount before taxes
- `tax_breakup`: Breakdown of all tax types
- `tax_total`: Sum of all taxes
- `grand_total`: `subtotal + tax_total + round_off`
- For registers: These are aggregated totals across all entries

### `entries` (array, required)
Array of entries/transactions/line items.

**For invoices:**
```json
[{
  "entry_id": "main-invoice",
  "entry_type": "invoice",
  "entry_date": "2025-01-15",
  "entry_number": "INV-001",
  "party": null,  // Uses top-level parties
  "line_items": [
    {
      "description": "Product Name",
      "hsn_sac": "8471",
      "quantity": 10.0,
      "unit": "NOS",
      "unit_price": 10000.00,
      "amount": 100000.00,
      "tax_rate": 18.0,
      "tax_amount": 18000.00
    }
  ],
  "amounts": {
    "taxable_value": 100000.00,
    "tax_breakup": {
      "cgst": 9000.00,
      "sgst": 9000.00,
      "igst": 0.00,
      "cess": 0.00
    },
    "total": 118000.00
  },
  "doc_specific": {}
}]
```

**For purchase/sales registers:**
```json
[{
  "entry_id": "entry-1",
  "entry_type": "register_entry",
  "entry_date": "2025-01-05",
  "entry_number": "PUR-001",
  "party": {
    "name": "Supplier Name",
    "gstin": "27XYZ9876543Z1B3",
    "state_code": "27"
  },
  "line_items": [],  // Usually empty for registers
  "amounts": {
    "taxable_value": 100000.00,
    "tax_breakup": {
      "cgst": 9000.00,
      "sgst": 9000.00,
      "igst": 0.00,
      "cess": 0.00
    },
    "total": 118000.00
  },
  "doc_specific": {
    "reverse_charge": false,
    "invoice_type": "REGULAR",
    "place_of_supply": "Maharashtra",
    "hsn_summary": []
  }
}]
```

**For bank statements:**
```json
[{
  "entry_id": "txn-1",
  "entry_type": "transaction",
  "entry_date": "2025-01-05",
  "entry_number": null,
  "party": null,
  "line_items": [],
  "amounts": {
    "amount": 1000.00,
    "balance": 50000.00
  },
  "doc_specific": {
    "description": "Payment received",
    "transaction_type": "credit",
    "reference": "CHQ123456",
    "channel": "cheque"
  }
}]
```

### `doc_specific` (object, required)
Document-type-specific fields that don't fit into the common structure.

**For invoices:**
```json
{
  "due_date": "2025-02-15",
  "po_number": "PO-123",
  "place_of_supply": "Maharashtra",
  "notes": "Payment terms: Net 30"
}
```

**For purchase/sales registers:**
```json
{
  "total_invoices": 5,
  "total_suppliers": 3  // or "total_customers" for sales
}
```

**For GSTR-3B:**
```json
{
  "gstr_form": "GSTR-3B",
  "turnover": 500000.00,
  "total_invoices": 10
}
```

## Usage

### API Endpoint

```
GET /v1/jobs/{job_id}?format=canonical
```

**Query Parameters:**
- `format`: `"legacy"` (default) or `"canonical"`

**Response:**
```json
{
  "job_id": "abc123",
  "status": "succeeded",
  "doc_type": "invoice",
  "filename": "invoice.pdf",
  "result": {
    // Canonical JSON structure
  },
  "meta": {
    "format": "canonical",
    "schema_version": "doc.v0.1"
  }
}
```

### Python Usage

```python
from api.app.parsers.canonical import normalize_to_canonical

# Convert parsed invoice to canonical format
parsed_invoice = {
    "invoice_number": "INV-001",
    "date": "2025-01-15",
    "seller": {"name": "ABC Corp", "gstin": "27ABCDE1234F1Z5"},
    "buyer": {"name": "XYZ Ltd", "gstin": "24XYZ9876543Z1B3"},
    "items": [...],
    "totals": {...}
}

canonical = normalize_to_canonical("invoice", parsed_invoice)
```

## Supported Document Types

- ✅ `invoice` / `gst_invoice`
- ✅ `purchase_register`
- ✅ `sales_register`
- ✅ `gstr3b` / `gstr`
- ⚠️ `gstr1` (partial)
- ⚠️ `bank_statement` (fallback only)
- ⚠️ Other types (fallback format)

## Migration Notes

- **Backward Compatible**: Legacy format remains default (`format=legacy`)
- **Opt-in**: Use `format=canonical` to get canonical format
- **Future**: Canonical will become default in v0.2

## Examples

See `CANONICAL_FORMAT_EXAMPLES.md` for side-by-side comparisons.

