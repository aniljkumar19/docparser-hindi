# Canonical JSON v0.1 - Implementation Summary

## ✅ Completed

### 1. Core Implementation
- **`api/app/parsers/canonical.py`**: Complete canonical format normalizer
  - `normalize_to_canonical()`: Main entry point
  - `_normalize_invoice_to_canonical()`: Invoice → canonical
  - `_normalize_purchase_register_to_canonical()`: Purchase register → canonical
  - `_normalize_sales_register_to_canonical()`: Sales register → canonical
  - `_normalize_gstr3b_to_canonical()`: GSTR-3B → canonical
  - `_normalize_gstr1_to_canonical()`: GSTR-1 → canonical (uses GSTR-3B logic)
  - Helper functions for date normalization, tax extraction, etc.

### 2. API Integration
- **`api/app/main.py`**: Updated `/v1/jobs/{job_id}` endpoint
  - Added `format` query parameter (`legacy` or `canonical`)
  - Default: `legacy` (backward compatible)
  - When `format=canonical`: Converts result to canonical format
  - Returns metadata indicating format used

### 3. Documentation
- **`CANONICAL_JSON_V0.1_SPEC.md`**: Complete specification
  - Field definitions
  - Structure for each document type
  - API usage examples
  - Migration notes

- **`CANONICAL_FORMAT_EXAMPLES.md`**: Quick reference
  - Side-by-side comparisons
  - Key changes summary

- **`CANONICAL_DOCUMENT_FORMAT.md`**: Original design document

### 4. Tests
- **`tests/test_canonical_format.py`**: Comprehensive test suite
  - Invoice conversion
  - Purchase register conversion
  - Sales register conversion
  - Taxes array handling
  - Edge cases

## 📋 Canonical Format Structure

```json
{
  "schema_version": "doc.v0.1",
  "doc_type": "invoice|purchase_register|sales_register|gstr3b|...",
  "doc_id": "unique-id",
  "doc_date": "YYYY-MM-DD" | null,
  "period": "YYYY-MM" | null,
  "metadata": {...},
  "business": {...},
  "parties": {
    "primary": {...},
    "counterparty": {...}  // optional
  },
  "financials": {
    "currency": "INR",
    "subtotal": 0.0,
    "tax_breakup": {
      "cgst": 0.0,
      "sgst": 0.0,
      "igst": 0.0,
      "cess": 0.0,
      "tds": 0.0,
      "tcs": 0.0
    },
    "tax_total": 0.0,
    "grand_total": 0.0
  },
  "entries": [...],
  "doc_specific": {...}
}
```

## 🚀 Usage

### API Endpoint

```bash
# Get job result in canonical format
GET /v1/jobs/{job_id}?format=canonical

# Get job result in legacy format (default)
GET /v1/jobs/{job_id}
```

### Python Code

```python
from api.app.parsers.canonical import normalize_to_canonical

# Convert any parsed document to canonical format
canonical = normalize_to_canonical("invoice", parsed_invoice_data)
canonical = normalize_to_canonical("purchase_register", parsed_register_data)
canonical = normalize_to_canonical("gstr3b", parsed_gstr_data)
```

## ✅ Supported Document Types

| Document Type | Status | Notes |
|--------------|--------|-------|
| `invoice` / `gst_invoice` | ✅ Complete | Full conversion with line items |
| `purchase_register` | ✅ Complete | Aggregated totals, per-entry parties |
| `sales_register` | ✅ Complete | Similar to purchase register |
| `gstr3b` / `gstr` | ✅ Complete | Period-based, tax aggregation |
| `gstr1` | ⚠️ Partial | Uses GSTR-3B logic (may need refinement) |
| `bank_statement` | ⚠️ Fallback | Basic structure only |
| Other types | ⚠️ Fallback | Wrapped in canonical structure with `doc_specific` |

## 🔄 Migration Path

1. **Phase 1 (Current)**: Dual output
   - Default: `format=legacy` (backward compatible)
   - Opt-in: `format=canonical`
   
2. **Phase 2 (Future)**: Canonical as default
   - Default: `format=canonical`
   - Legacy available: `format=legacy`
   
3. **Phase 3 (Future)**: Legacy deprecation
   - Remove legacy format after migration period

## 📝 Key Features

1. **Unified Structure**: All documents follow same top-level structure
2. **Consistent Fields**: `parties`, `financials`, `entries` always in same format
3. **Type-Specific**: `doc_specific` section for document-specific fields
4. **Backward Compatible**: Legacy format remains default
5. **Extensible**: Easy to add new document types

## 🧪 Testing

Run tests:
```bash
pytest tests/test_canonical_format.py -v
```

Test coverage:
- ✅ Invoice conversion
- ✅ Purchase register conversion
- ✅ Sales register conversion
- ✅ Taxes array handling
- ✅ Date normalization
- ✅ GSTIN state code extraction

## 📚 Files Created/Modified

### New Files
- `api/app/parsers/canonical.py` - Core normalizer implementation
- `CANONICAL_JSON_V0.1_SPEC.md` - Complete specification
- `CANONICAL_FORMAT_EXAMPLES.md` - Quick reference
- `CANONICAL_IMPLEMENTATION_SUMMARY.md` - This file
- `tests/test_canonical_format.py` - Test suite

### Modified Files
- `api/app/main.py` - Added `format` parameter to `/v1/jobs/{job_id}` endpoint

## 🎯 Next Steps (Optional)

1. **Enhance GSTR-1**: Add GSTR-1 specific fields
2. **Bank Statement**: Complete bank statement normalization
3. **Exporters**: Update Tally/Zoho exporters to use canonical format
4. **Dashboard**: Add format toggle in UI
5. **Validation**: Add JSON schema validation for canonical format
6. **Documentation**: Add API documentation examples

## 💡 Design Decisions

1. **Always use arrays for entries**: Even single-entry documents use `entries[]` array
2. **Consistent tax structure**: Always `tax_breakup` object with same fields
3. **State code extraction**: Automatically extract from GSTIN (first 2 digits)
4. **Date normalization**: Convert all dates to `YYYY-MM-DD` format
5. **Fallback handling**: Unknown types wrapped in canonical structure with original data in `doc_specific`

