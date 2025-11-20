# Canonical Document Format Design

## Overview

This document proposes a unified, canonical JSON format that works for all document types in the DocParser system. The goal is to standardize the output structure while maintaining flexibility for document-specific fields.

## Design Principles

1. **Unified Structure**: All documents follow the same top-level structure
2. **Type-Specific Extensions**: Document-specific fields are organized under `doc_specific` or type-appropriate sections
3. **Backward Compatibility**: Existing integrations continue to work during migration
4. **Extensibility**: Easy to add new document types without breaking changes
5. **Consistency**: Common fields (dates, parties, amounts, taxes) use standardized formats

## Canonical Structure

```json
{
  "schema_version": "doc.v1",
  "doc_type": "invoice|purchase_register|sales_register|bank_statement|utility_bill|gstr|gstr3b|gstr1|receipt|eway_bill",
  "doc_id": "unique-document-identifier",
  "doc_date": "YYYY-MM-DD",
  "period": "YYYY-MM" | null,  // For period-based documents (registers, GSTR)
  
  // Common metadata
  "metadata": {
    "source_filename": "original.pdf",
    "parser_version": "parser_v1",
    "processing_timestamp": "2025-01-15T10:30:00Z",
    "confidence_score": 0.95,
    "warnings": [],
    "raw_data": {}  // Optional: preserve original structure
  },
  
  // Business entity (company/business that owns this document)
  "business": {
    "name": "Company Name",
    "gstin": "27ABCDE1234F1Z5",
    "address": {},
    "state_code": "27"
  },
  
  // Parties (seller/buyer/customer/supplier)
  "parties": {
    "primary": {  // Seller for invoices, Company for registers
      "name": "ABC Corp",
      "gstin": "27ABCDE1234F1Z5",
      "address": {},
      "state_code": "27"
    },
    "counterparty": {  // Buyer for invoices, Supplier/Customer for registers
      "name": "XYZ Ltd",
      "gstin": "24XYZ9876543Z1B3",
      "address": {},
      "state_code": "24"
    }
  },
  
  // Financial summary (aggregated totals)
  "financials": {
    "currency": "INR",
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
  },
  
  // Entries/Transactions/Items (varies by document type)
  "entries": [
    {
      "entry_id": "entry-1",
      "entry_type": "invoice|transaction|line_item|register_entry",
      "entry_date": "YYYY-MM-DD",
      "entry_number": "INV-001",
      
      // Party info (if different from top-level)
      "party": {
        "name": "Supplier Name",
        "gstin": "24XYZ9876543Z1B3"
      },
      
      // Financial details for this entry
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
      
      // Line items (for invoices/registers with item details)
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
      
      // Document-specific fields
      "doc_specific": {
        // Type-specific fields go here
      }
    }
  ],
  
  // Document-specific top-level fields
  "doc_specific": {
    // Fields that don't fit into common structure
  }
}
```

## Document Type Mappings

### 1. Invoice / GST Invoice

**Current Structure:**
```json
{
  "invoice_number": "...",
  "date": "...",
  "seller": {...},
  "buyer": {...},
  "items": [...],
  "tax_breakup": {...},
  "totals": {...}
}
```

**Canonical Structure:**
```json
{
  "schema_version": "doc.v1",
  "doc_type": "invoice",
  "doc_id": "inv-2025-001",
  "doc_date": "2025-01-15",
  "metadata": {...},
  "business": {
    "name": "Seller Company",
    "gstin": "27ABCDE1234F1Z5"
  },
  "parties": {
    "primary": {
      "name": "Seller Company",
      "gstin": "27ABCDE1234F1Z5"
    },
    "counterparty": {
      "name": "Buyer Company",
      "gstin": "24XYZ9876543Z1B3"
    }
  },
  "financials": {
    "currency": "INR",
    "subtotal": 100000.00,
    "tax_breakup": {...},
    "tax_total": 18000.00,
    "grand_total": 118000.00
  },
  "entries": [
    {
      "entry_id": "main-invoice",
      "entry_type": "invoice",
      "entry_date": "2025-01-15",
      "entry_number": "INV-001",
      "line_items": [...],
      "amounts": {
        "taxable_value": 100000.00,
        "total": 118000.00
      }
    }
  ],
  "doc_specific": {
    "due_date": "2025-02-15",
    "po_number": "PO-123",
    "place_of_supply": "Maharashtra"
  }
}
```

### 2. Purchase Register

**Current Structure:**
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
      "supplier_gstin": "24XYZ9876543Z1B3",
      "taxable_value": 100000.00,
      "cgst": 9000.00,
      "sgst": 9000.00,
      "total_value": 118000.00
    }
  ]
}
```

**Canonical Structure:**
```json
{
  "schema_version": "doc.v1",
  "doc_type": "purchase_register",
  "doc_id": "purchase-reg-2025-01",
  "doc_date": null,
  "period": "2025-01",
  "metadata": {...},
  "business": {
    "name": "Company Name",
    "gstin": "27ABCDE1234F1Z5",
    "state_code": "27"
  },
  "parties": {
    "primary": {
      "name": "Company Name",
      "gstin": "27ABCDE1234F1Z5"
    }
  },
  "financials": {
    "currency": "INR",
    "subtotal": 500000.00,  // Sum of all entries
    "tax_breakup": {
      "cgst": 45000.00,
      "sgst": 45000.00,
      "igst": 0.00
    },
    "tax_total": 90000.00,
    "grand_total": 590000.00
  },
  "entries": [
    {
      "entry_id": "entry-1",
      "entry_type": "register_entry",
      "entry_date": "2025-01-05",
      "entry_number": "PUR-001",
      "party": {
        "name": "XYZ Distributors",
        "gstin": "24XYZ9876543Z1B3",
        "state_code": "24"
      },
      "amounts": {
        "taxable_value": 100000.00,
        "tax_breakup": {
          "cgst": 9000.00,
          "sgst": 9000.00,
          "igst": 0.00
        },
        "total": 118000.00
      },
      "doc_specific": {
        "reverse_charge": false,
        "invoice_type": "REGULAR",
        "place_of_supply": "Maharashtra",
        "hsn_summary": []
      }
    }
  ],
  "doc_specific": {
    "total_invoices": 5,
    "total_suppliers": 3
  }
}
```

### 3. Sales Register

**Similar to Purchase Register, but:**
- `doc_type`: `"sales_register"`
- `party` uses `customer_name` / `customer_gstin` instead of `supplier_name` / `supplier_gstin`
- `entry_type`: `"register_entry"` (same)

### 4. Bank Statement

**Current Structure:**
```json
{
  "account_number": "...",
  "period": "2025-01",
  "transactions": [
    {
      "date": "2025-01-05",
      "description": "...",
      "amount": 1000.00,
      "balance": 50000.00
    }
  ]
}
```

**Canonical Structure:**
```json
{
  "schema_version": "doc.v1",
  "doc_type": "bank_statement",
  "doc_id": "bank-stmt-2025-01",
  "doc_date": null,
  "period": "2025-01",
  "metadata": {...},
  "business": {
    "name": "Account Holder Name"
  },
  "financials": {
    "currency": "INR",
    "opening_balance": 45000.00,
    "closing_balance": 50000.00,
    "total_debits": 10000.00,
    "total_credits": 15000.00
  },
  "entries": [
    {
      "entry_id": "txn-1",
      "entry_type": "transaction",
      "entry_date": "2025-01-05",
      "entry_number": null,
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
    }
  ],
  "doc_specific": {
    "account_number": "1234567890",
    "bank_name": "HDFC Bank",
    "ifsc": "HDFC0001234"
  }
}
```

### 5. GSTR / GSTR3B / GSTR1

**Current Structure:**
```json
{
  "gstr_form": "GSTR-3B",
  "period": "2025-01",
  "gstin": "27ABCDE1234F1Z5",
  "taxes": [...],
  "invoices": [...]
}
```

**Canonical Structure:**
```json
{
  "schema_version": "doc.v1",
  "doc_type": "gstr3b",
  "doc_id": "gstr3b-2025-01",
  "doc_date": null,
  "period": "2025-01",
  "metadata": {...},
  "business": {
    "name": "Company Name",
    "gstin": "27ABCDE1234F1Z5",
    "state_code": "27"
  },
  "financials": {
    "currency": "INR",
    "tax_breakup": {
      "cgst": 45000.00,
      "sgst": 45000.00,
      "igst": 0.00,
      "cess": 0.00
    },
    "tax_total": 90000.00
  },
  "entries": [
    {
      "entry_id": "gstr-entry-1",
      "entry_type": "gstr_entry",
      "entry_date": "2025-01-05",
      "entry_number": "INV-001",
      "amounts": {
        "taxable_value": 100000.00,
        "tax_breakup": {...},
        "total": 118000.00
      },
      "doc_specific": {
        "place_of_supply": "Maharashtra",
        "reverse_charge": false
      }
    }
  ],
  "doc_specific": {
    "gstr_form": "GSTR-3B",
    "turnover": 500000.00,
    "total_invoices": 10
  }
}
```

## Migration Strategy

### Phase 1: Dual Output (Backward Compatible)
- Add canonical format alongside existing format
- Use query parameter: `?format=canonical` or `?format=legacy`
- Default to `legacy` for backward compatibility

### Phase 2: Canonical as Default
- Make canonical format the default
- Keep legacy format available via `?format=legacy`
- Update all exporters (Tally, Zoho, CSV) to use canonical format

### Phase 3: Legacy Deprecation
- Deprecate legacy format
- Remove after sufficient migration period

## Implementation Plan

### Step 1: Create Canonical Normalizer
- Create `api/app/parsers/canonical.py`
- Function: `normalize_to_canonical(doc_type: str, parsed_data: dict) -> dict`
- Maps each document type to canonical format

### Step 2: Update API Endpoints
- Modify `/v1/jobs/{job_id}` to support `?format=canonical`
- Update job storage to include canonical format (optional field)
- Add validation for canonical format

### Step 3: Update Exporters
- Modify Tally XML/CSV exporters to use canonical format
- Update Zoho exporter
- Update other format exporters

### Step 4: Update Dashboard
- Display canonical format in UI
- Add format toggle (canonical vs legacy)

### Step 5: Documentation
- Update API documentation
- Create migration guide
- Add examples for each document type

## Benefits

1. **Consistency**: All documents follow the same structure
2. **Easier Integration**: Clients only need to learn one format
3. **Better Validation**: Single schema for all document types
4. **Simplified Exporters**: Exporters can work with one format
5. **Future-Proof**: Easy to add new document types

## Open Questions

1. Should we preserve the original structure in `metadata.raw_data`?
2. How to handle documents with multiple periods (e.g., multi-month statements)?
3. Should `entries` always be an array, even for single-entry documents?
4. How to handle nested structures (e.g., GSTR with multiple tables)?
5. Should we version the canonical format (`doc.v1`, `doc.v2`)?

## Next Steps

1. Review and discuss this design
2. Create prototype implementation
3. Test with existing documents
4. Get feedback from stakeholders
5. Finalize and implement

