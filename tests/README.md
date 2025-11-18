# Test Suite for DocParser

This directory contains all test scripts and fixtures for validating DocParser functionality.

## Structure

```
tests/
├── README.md                          # This file
├── conftest.py                        # Pytest configuration (imports setup)
├── pytest.ini                         # Pytest settings
├── test_tally_xml_gst_autofix.py      # ✅ Pytest: GST auto-fix regression tests
├── test_tally_xml_structure.py        # ✅ Pytest: XML structure validation tests
├── test_gst_auto_fix.py               # Legacy: Manual GST auto-fix tests
├── show_xml_output.py                 # Legacy: Visual XML output viewer
├── test_db_connection.py              # Database connection tests
├── test_bulk_processing.py            # Bulk processing tests
├── run_tally_tests.sh                # Quick test runner script
└── fixtures/                          # Test data files
    ├── purchase_same_state.json       # Sample: Same state purchase (should use CGST+SGST)
    ├── purchase_different_state.json  # Sample: Different state purchase (should use IGST)
    └── tally_purchase_sample.xml      # Golden sample XML for Tally imports
```

## Running Tests

### Pytest Tests (Recommended - Regression Tests)

**Run all Tally XML tests:**
```bash
# From project root
pytest tests/test_tally_xml_*.py -v

# Or from tests directory
cd tests && pytest test_tally_xml_*.py -v
```

**Run specific test file:**
```bash
pytest tests/test_tally_xml_gst_autofix.py -v
pytest tests/test_tally_xml_structure.py -v
```

**Run with coverage:**
```bash
pytest tests/test_tally_xml_*.py --cov=app.exporters.tally_xml --cov-report=term
```

### Manual Test Scripts (Legacy)

**GST Auto-Fix Tests:**
```bash
cd tests
python3 test_gst_auto_fix.py
```

**View XML output:**
```bash
cd tests
python3 show_xml_output.py
```

**What it tests:**
- ✅ Same state transactions → Auto-converts IGST to CGST+SGST
- ✅ Different state transactions → Auto-converts CGST+SGST to IGST
- ✅ Voucher number uniqueness
- ✅ Tax amount calculations

### Database Connection Tests

```bash
cd tests
python3 test_db_connection.py
```

### Bulk Processing Tests

```bash
cd tests
python3 test_bulk_processing.py
```

## Test Fixtures

### JSON Input Files

- **`purchase_same_state.json`**: Purchase invoice with same state supplier (27)
  - Has IGST initially → Should be auto-fixed to CGST+SGST
  
- **`purchase_different_state.json`**: Purchase invoice with different state supplier (24)
  - Has CGST+SGST initially → Should be auto-fixed to IGST

### XML Sample Files

- **`tally_purchase_sample.xml`**: Golden sample XML for Tally imports
  - Reference format for Tally purchase voucher structure
  - Use this to validate generated XML matches expected format

## When to Run Tests

**Always run these tests when:**
- ✅ Modifying Tally XML/CSV export logic
- ✅ Changing GST calculation or auto-fix logic
- ✅ Updating voucher number generation
- ✅ Modifying ledger entry structures
- ✅ Before deploying to production

**Quick test command:**
```bash
cd tests && python3 test_gst_auto_fix.py && echo "✅ All tests passed!"
```

## Test Coverage

### Pytest Tests (test_tally_xml_gst_autofix.py)
- [x] Same state → CGST+SGST conversion
- [x] Different state → IGST conversion
- [x] Tax amount accuracy (splitting/summing)
- [x] Voucher number uniqueness
- [x] IGST to CGST+SGST amount validation (50/50 split)
- [x] CGST+SGST to IGST amount validation (sum)

### Pytest Tests (test_tally_xml_structure.py)
- [x] Required tags validation (VCHTYPE, VOUCHERTYPENAME, DATE, etc.)
- [x] Recommended tags check (EFFECTIVEDATE, PARTYGSTIN, ISINVOICE)
- [x] Voucher balancing (debits = credits)
- [x] XML syntax validation
- [x] Date format validation (YYYYMMDD)
- [x] VCHTYPE validation (Purchase vs Sales)
- [x] Sign convention validation (debits positive, credits negative)

### Future Test Additions
- [ ] Duplicate voucher number auto-fix (for register documents)
- [ ] Stock item name normalization
- [ ] Multiple line items handling
- [ ] Discount handling
- [ ] Round-off amount handling

## Notes

- Tests use hardcoded test data (no database required for GST tests)
- Tests directly call `invoice_to_tally_xml()` function
- Company state code is set to "27" (Maharashtra) in tests
- Modify test data in fixtures/ to test different scenarios

## Troubleshooting

**Import errors:**
- Make sure you're running from the `tests/` directory
- Check that `api/` directory exists at project root

**Test failures:**
- Check logs for detailed error messages
- Verify company state code matches test expectations
- Ensure test fixtures are in `fixtures/` directory

