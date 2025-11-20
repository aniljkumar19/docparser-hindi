# Canonical Document Format v0.1 - Modular Normalizers

This directory contains modular normalizers for converting various document types into a unified canonical JSON format.

## Structure

```
canonical/
├── __init__.py              # Main entry point - routes to appropriate normalizer
├── base.py                  # Shared utility functions
├── invoice_normalizer.py    # Invoice → canonical
├── register_normalizer.py  # Purchase/Sales register → canonical
├── gstr3b_normalizer.py     # GSTR-3B → canonical
├── gstr1_normalizer.py     # GSTR-1 → canonical
├── bank_statement_normalizer.py  # Bank statement → canonical (TODO)
└── fallback_normalizer.py  # Unknown types → canonical wrapper
```

## Usage

```python
from api.app.parsers.canonical import normalize_to_canonical

# Convert any document type
canonical = normalize_to_canonical(doc_type="invoice", parsed_data=invoice_data)
canonical = normalize_to_canonical(doc_type="gstr3b", parsed_data=gstr3b_data)
canonical = normalize_to_canonical(doc_type="sales_register", parsed_data=register_data)
```

## Adding a New Document Type

1. Create a new normalizer file: `{doc_type}_normalizer.py`
2. Implement `normalize_{doc_type}_to_canonical(parsed: Dict[str, Any]) -> Dict[str, Any]`
3. Import and add routing in `__init__.py`:

```python
from .{doc_type}_normalizer import normalize_{doc_type}_to_canonical

# In normalize_to_canonical():
elif doc_type == "{doc_type}":
    return normalize_{doc_type}_to_canonical(parsed_data)
```

## Canonical Format Schema

All normalizers output the same structure:

```json
{
  "schema_version": "doc.v0.1",
  "doc_type": "invoice|gstr3b|sales_register|...",
  "doc_id": "unique-id",
  "doc_date": "YYYY-MM-DD",
  "period": "period-label",
  "metadata": {
    "source_format": "...",
    "parser_version": "...",
    "warnings": []
  },
  "business": {
    "name": "...",
    "gstin": "...",
    "state_code": "..."
  },
  "parties": {
    "primary": {...},
    "counterparty": {...}
  },
  "financials": {
    "currency": "INR",
    "subtotal": 0.0,
    "tax_breakup": {...},
    "tax_total": 0.0,
    "grand_total": 0.0
  },
  "entries": [...],
  "doc_specific": {...}
}
```

## Benefits of Modular Design

✅ **Easy to maintain** - Each document type has its own file  
✅ **Easy to extend** - Add new types without touching existing code  
✅ **Easy to test** - Test each normalizer independently  
✅ **Clear separation** - Shared utilities in `base.py`, type-specific logic in normalizers  
✅ **Better organization** - No giant monolithic file

