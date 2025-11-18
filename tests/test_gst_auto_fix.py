#!/usr/bin/env python3
"""
Test script to verify GST auto-fix logic for Tally XML generation.

Tests two scenarios:
1. Same state (27) - should use CGST+SGST
2. Different state (24) - should use IGST
"""

import sys
import os

# Add the api directory to the path (tests/ is one level up from api/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from app.exporters.tally_xml import invoice_to_tally_xml

# Company state code (first 2 digits of company GSTIN)
COMPANY_STATE_CODE = "27"  # Maharashtra

# Test Purchase 1: Same state (27) - should use CGST+SGST
# Currently has IGST, should be auto-fixed to CGST+SGST
purchase1 = {
    "invoice_number": "TEST-001",
    "date": "2025-01-15",
    "buyer": {
        "name": "Intra Supplier",
        "gstin": "27ABCDEF1234Z1A2"  # Same state as company (27)
    },
    "subtotal": 10000,
    "total": 11800,
    "cgst": 0,  # Initially 0 - will be auto-fixed
    "sgst": 0,  # Initially 0 - will be auto-fixed
    "igst": 1800,  # Has IGST - should be converted to CGST+SGST
    "taxes": [
        {"type": "IGST", "amount": 1800}
    ],
    "line_items": [{
        "desc": "Test Item 1",
        "qty": 1,
        "unit_price": 10000,
        "amount": 10000
    }]
}

# Test Purchase 2: Different state (24) - should use IGST
# Currently has CGST+SGST, should be auto-fixed to IGST
purchase2 = {
    "invoice_number": "TEST-002",
    "date": "2025-01-16",
    "buyer": {
        "name": "Inter Supplier",
        "gstin": "24XYZ9876543Z1B3"  # Different state (24 = Gujarat)
    },
    "subtotal": 20000,
    "total": 23600,
    "cgst": 1800,  # Has CGST - should be converted to IGST
    "sgst": 1800,  # Has SGST - should be converted to IGST
    "igst": 0,  # Initially 0 - will be auto-fixed
    "taxes": [
        {"type": "CGST", "amount": 1800},
        {"type": "SGST", "amount": 1800}
    ],
    "line_items": [{
        "desc": "Test Item 2",
        "qty": 1,
        "unit_price": 20000,
        "amount": 20000
    }]
}

def check_xml_contains(xml, must_contain, must_not_contain, voucher_name):
    """Check if XML contains required elements and doesn't contain forbidden ones."""
    print(f"\n{'='*60}")
    print(f"Testing {voucher_name}")
    print(f"{'='*60}")
    
    all_passed = True
    
    # Check must contain
    for item in must_contain:
        if item in xml:
            print(f"✅ PASS: Found '{item}'")
        else:
            print(f"❌ FAIL: Missing '{item}'")
            all_passed = False
    
    # Check must not contain
    for item in must_not_contain:
        if item not in xml:
            print(f"✅ PASS: Correctly absent '{item}'")
        else:
            print(f"❌ FAIL: Should not contain '{item}'")
            all_passed = False
    
    return all_passed

def main():
    print("🧪 Testing GST Auto-Fix Logic")
    print(f"Company State Code: {COMPANY_STATE_CODE}")
    
    # Generate XML for Purchase 1 (same state - should use CGST+SGST)
    print("\n📝 Generating XML for Purchase 1 (Same State - 27)...")
    xml1 = invoice_to_tally_xml(
        purchase1,
        voucher_type="Purchase",
        company_state_code=COMPANY_STATE_CODE
    )
    
    # Check Purchase 1: Should have CGST+SGST, NO IGST
    result1 = check_xml_contains(
        xml1,
        must_contain=[
            "Input CGST",
            "Input SGST",
            "TEST-001"
        ],
        must_not_contain=[
            "Input IGST"
        ],
        voucher_name="Purchase 1 (Same State - Should use CGST+SGST)"
    )
    
    # Generate XML for Purchase 2 (different state - should use IGST)
    print("\n📝 Generating XML for Purchase 2 (Different State - 24)...")
    xml2 = invoice_to_tally_xml(
        purchase2,
        voucher_type="Purchase",
        company_state_code=COMPANY_STATE_CODE
    )
    
    # Check Purchase 2: Should have IGST, NO CGST, NO SGST
    result2 = check_xml_contains(
        xml2,
        must_contain=[
            "Input IGST",
            "TEST-002"
        ],
        must_not_contain=[
            "Input CGST",
            "Input SGST"
        ],
        voucher_name="Purchase 2 (Different State - Should use IGST)"
    )
    
    # Check voucher numbers are different
    print(f"\n{'='*60}")
    print("Checking Voucher Numbers")
    print(f"{'='*60}")
    if "TEST-001" in xml1 and "TEST-002" in xml2:
        print("✅ PASS: Voucher numbers are different (TEST-001 vs TEST-002)")
        result3 = True
    else:
        print("❌ FAIL: Voucher numbers are not correct")
        result3 = False
    
    # Final summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    if result1 and result2 and result3:
        print("✅ ALL TESTS PASSED!")
        print("\nThe GST auto-fix logic is working correctly:")
        print("  - Same state transactions → CGST+SGST")
        print("  - Different state transactions → IGST")
        print("  - Voucher numbers are unique")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        if not result1:
            print("  - Purchase 1 (same state) failed")
        if not result2:
            print("  - Purchase 2 (different state) failed")
        if not result3:
            print("  - Voucher number check failed")
        return 1

if __name__ == "__main__":
    exit(main())

