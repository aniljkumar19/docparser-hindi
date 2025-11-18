"""
Pytest tests for GST auto-fix logic in Tally XML generation.

These tests ensure that:
- Same state transactions use CGST+SGST (IGST auto-converted)
- Different state transactions use IGST (CGST+SGST auto-converted)
- Voucher numbers are unique
"""

import re
import sys
import os

# Add api directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from app.exporters.tally_xml import invoice_to_tally_xml

COMPANY_STATE_CODE = "27"  # Maharashtra


def _make_invoice_same_state():
    """Same state as company: should end up CGST + SGST"""
    return {
        "invoice_number": "TEST-001",
        "date": "2025-01-15",
        "buyer": {"name": "Intra Supplier", "gstin": "27ABCDEF1234Z1A2"},
        "subtotal": 10000,
        "total": 11800,
        # Intentionally coming in as IGST to test auto-fix
        "igst": 1800,
        "taxes": [{"type": "IGST", "amount": 1800}],
        "line_items": [
            {
                "desc": "Test Item",
                "qty": 1,
                "unit_price": 10000,
                "amount": 10000,
            }
        ],
    }


def _make_invoice_diff_state():
    """Different state: should end up IGST only"""
    return {
        "invoice_number": "TEST-002",
        "date": "2025-01-16",
        "buyer": {"name": "Inter Supplier", "gstin": "24XYZ9876543Z1B3"},
        "subtotal": 20000,
        "total": 23600,
        # Intentionally coming in as CGST+SGST to test auto-fix
        "cgst": 1800,
        "sgst": 1800,
        "taxes": [
            {"type": "CGST", "amount": 1800},
            {"type": "SGST", "amount": 1800},
        ],
        "line_items": [
            {
                "desc": "Test Item",
                "qty": 1,
                "unit_price": 20000,
                "amount": 20000,
            }
        ],
    }


def test_same_state_uses_cgst_sgst():
    """Test that same state transactions use CGST+SGST (IGST auto-converted)"""
    invoice = _make_invoice_same_state()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Should have CGST + SGST, no IGST
    assert "Input CGST" in xml, "Same state transaction should have Input CGST"
    assert "Input SGST" in xml, "Same state transaction should have Input SGST"
    assert "Input IGST" not in xml, "Same state transaction should NOT have Input IGST"

    # Voucher number appears
    assert "TEST-001" in xml, "Voucher number should appear in XML"


def test_diff_state_uses_igst():
    """Test that different state transactions use IGST (CGST+SGST auto-converted)"""
    invoice = _make_invoice_diff_state()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Should have IGST only
    assert "Input IGST" in xml, "Different state transaction should have Input IGST"
    assert "Input CGST" not in xml, "Different state transaction should NOT have Input CGST"
    assert "Input SGST" not in xml, "Different state transaction should NOT have Input SGST"

    assert "TEST-002" in xml, "Voucher number should appear in XML"


def test_voucher_numbers_unique_between_invoices():
    """Test that voucher numbers are unique between different invoices"""
    inv1 = _make_invoice_same_state()
    inv2 = _make_invoice_diff_state()

    xml1 = invoice_to_tally_xml(
        inv1, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )
    xml2 = invoice_to_tally_xml(
        inv2, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Extract voucher numbers from XML (simple regex)
    def extract_vch_number(xml: str) -> str:
        m = re.search(r"<VOUCHERNUMBER>(.*?)</VOUCHERNUMBER>", xml)
        assert m, "Missing <VOUCHERNUMBER> in XML"
        return m.group(1)

    v1 = extract_vch_number(xml1)
    v2 = extract_vch_number(xml2)

    assert v1 != v2, f"Voucher numbers should differ, got {v1} and {v2}"


def test_same_state_igst_converted_to_cgst_sgst_amounts():
    """Test that IGST is correctly split into CGST+SGST (50/50) for same state"""
    invoice = _make_invoice_same_state()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Extract CGST and SGST amounts
    cgst_match = re.search(r'<LEDGERNAME>Input CGST</LEDGERNAME>.*?<AMOUNT>([0-9\.]+)</AMOUNT>', xml, re.DOTALL)
    sgst_match = re.search(r'<LEDGERNAME>Input SGST</LEDGERNAME>.*?<AMOUNT>([0-9\.]+)</AMOUNT>', xml, re.DOTALL)

    assert cgst_match, "CGST amount should be present"
    assert sgst_match, "SGST amount should be present"

    cgst_amount = float(cgst_match.group(1))
    sgst_amount = float(sgst_match.group(1))

    # Original IGST was 1800, should be split 50/50 = 900 each
    assert abs(cgst_amount - 900.0) < 0.01, f"CGST should be 900.0, got {cgst_amount}"
    assert abs(sgst_amount - 900.0) < 0.01, f"SGST should be 900.0, got {sgst_amount}"
    assert abs(cgst_amount - sgst_amount) < 0.01, "CGST and SGST should be equal"


def test_diff_state_cgst_sgst_converted_to_igst_amount():
    """Test that CGST+SGST is correctly summed into IGST for different state"""
    invoice = _make_invoice_diff_state()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Extract IGST amount
    igst_match = re.search(r'<LEDGERNAME>Input IGST</LEDGERNAME>.*?<AMOUNT>([0-9\.]+)</AMOUNT>', xml, re.DOTALL)

    assert igst_match, "IGST amount should be present"

    igst_amount = float(igst_match.group(1))

    # Original CGST+SGST was 1800+1800 = 3600, should become IGST 3600
    assert abs(igst_amount - 3600.0) < 0.01, f"IGST should be 3600.0, got {igst_amount}"

