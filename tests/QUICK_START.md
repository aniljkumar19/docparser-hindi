# Quick Start: Running Tally XML Tests

## Prerequisites

```bash
# Install pytest (if not already installed)
pip install pytest

# Or if using requirements.txt
pip install -r api/requirements.txt
```

## Run All Tally Tests

```bash
# From project root
pytest tests/test_tally_xml_*.py -v
```

## Run Specific Test File

```bash
# GST auto-fix tests
pytest tests/test_tally_xml_gst_autofix.py -v

# Structure validation tests
pytest tests/test_tally_xml_structure.py -v
```

## Run Single Test

```bash
# Run specific test function
pytest tests/test_tally_xml_gst_autofix.py::test_same_state_uses_cgst_sgst -v
```

## Pre-commit Hook (Optional)

To automatically run tests before commits:

```bash
# Install pre-commit
pip install pre-commit

# Install the hook
pre-commit install

# Now tests will run automatically on every commit
```

## What Gets Tested

### GST Auto-Fix (`test_tally_xml_gst_autofix.py`)
- ✅ Same state → CGST+SGST conversion
- ✅ Different state → IGST conversion
- ✅ Tax amount accuracy
- ✅ Voucher number uniqueness

### Structure Validation (`test_tally_xml_structure.py`)
- ✅ Required tags present
- ✅ Voucher balancing (debits = credits)
- ✅ XML syntax validity
- ✅ Date format (YYYYMMDD)
- ✅ Sign conventions

## Troubleshooting

**Import errors:**
- Make sure you're running from project root
- Check that `api/` directory exists
- Verify `conftest.py` is in `tests/` directory

**Tests fail:**
- Check logs for detailed error messages
- Verify company state code matches test expectations
- Ensure test fixtures are in `fixtures/` directory

