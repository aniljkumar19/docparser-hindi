# Test Suite for DocParser

This directory contains all test scripts and fixtures for validating DocParser functionality.

## Structure

```
tests/
├── README.md                          # This file
├── test_gst_auto_fix.py               # GST auto-fix validation tests
├── show_xml_output.py                 # Visual XML output viewer
├── test_db_connection.py              # Database connection tests
├── test_bulk_processing.py            # Bulk processing tests
└── fixtures/                          # Test data files
    ├── purchase_same_state.json       # Sample: Same state purchase (should use CGST+SGST)
    ├── purchase_different_state.json  # Sample: Different state purchase (should use IGST)
    └── tally_purchase_sample.xml      # Golden sample XML for Tally imports
```

## Running Tests

### GST Auto-Fix Tests (Tally Export)

**Main test suite:**
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

### GST Auto-Fix Logic
- [x] Same state → CGST+SGST conversion
- [x] Different state → IGST conversion
- [x] Tax amount accuracy (splitting/summing)
- [x] Voucher number uniqueness
- [x] XML structure validation

### Future Test Additions
- [ ] Duplicate voucher number auto-fix
- [ ] Ledger balancing validation
- [ ] Sign convention validation
- [ ] Required/recommended tag validation
- [ ] Stock item name normalization
- [ ] Date format validation

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

