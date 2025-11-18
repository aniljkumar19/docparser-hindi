"""
Pytest tests for Tally XML structure validation.

These tests ensure that:
- Required tags are present
- Voucher balances (debits = credits)
- Sign conventions are correct
- XML structure is valid
"""

import re
import sys
import os
from decimal import Decimal
import xml.etree.ElementTree as ET

# Add api directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from app.exporters.tally_xml import invoice_to_tally_xml

COMPANY_STATE_CODE = "27"


def _sample_invoice():
    """Sample invoice for structure testing"""
    return {
        "invoice_number": "STRUCT-001",
        "date": "2025-01-20",
        "buyer": {"name": "Structure Supplier", "gstin": "27AAAAB1234Z1A1"},
        "subtotal": 100000,
        "total": 118000,
        "taxes": [{"type": "IGST", "amount": 18000}],
        "igst": 18000,
        "line_items": [
            {
                "desc": "Big Item",
                "qty": 1,
                "unit_price": 100000,
                "amount": 100000,
            }
        ],
    }


def test_voucher_has_required_tags():
    """Test that all required tags are present in the voucher XML"""
    invoice = _sample_invoice()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Required top-level tags inside <VOUCHER>
    required_tags = [
        "VCHTYPE",
        "VOUCHERTYPENAME",
        "DATE",
        "VOUCHERNUMBER",
        "PARTYLEDGERNAME",
    ]
    for tag in required_tags:
        assert f"<{tag}>" in xml, f"Missing required tag <{tag}> in Tally XML"


def test_voucher_has_recommended_tags():
    """Test that recommended tags are present (warnings if missing, but not failures)"""
    invoice = _sample_invoice()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Recommended tags (nice to have)
    recommended_tags = [
        "EFFECTIVEDATE",
        "PARTYGSTIN",
        "ISINVOICE",
    ]
    
    missing_tags = []
    for tag in recommended_tags:
        if f"<{tag}>" not in xml:
            missing_tags.append(tag)
    
    # Log warning but don't fail (these are recommended, not required)
    if missing_tags:
        print(f"⚠️  Recommended tags missing: {', '.join(missing_tags)}")


def test_voucher_balances_debits_and_credits():
    """Test that voucher balances (debits = credits)"""
    invoice = _sample_invoice()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Extract all ledger entries
    entries = re.findall(
        r"<ALLLEDGERENTRIES\.LIST>(.*?)</ALLLEDGERENTRIES\.LIST>", xml, re.DOTALL
    )

    assert entries, "No <ALLLEDGERENTRIES.LIST> found in XML"

    debit_sum = Decimal("0.00")
    credit_sum = Decimal("0.00")

    for entry in entries:
        # Get amount
        m_amount = re.search(r"<AMOUNT>([-0-9\.]+)</AMOUNT>", entry)
        if not m_amount:
            continue
        amount = Decimal(m_amount.group(1))

        m_deemed = re.search(r"<ISDEEMEDPOSITIVE>(Yes|No)</ISDEEMEDPOSITIVE>", entry)
        is_deemed_positive = m_deemed.group(1) == "Yes" if m_deemed else None

        # Convention:
        # - Debits: ISDEEMEDPOSITIVE = No, amount positive
        # - Credits: ISDEEMEDPOSITIVE = Yes, amount negative
        if is_deemed_positive is True:
            # credit line
            credit_sum += abs(amount)
        else:
            # debit line
            debit_sum += abs(amount)

    diff = abs(debit_sum - credit_sum)
    assert diff <= Decimal("0.01"), (
        f"Voucher not balanced: debits={debit_sum}, credits={credit_sum}, diff={diff}"
    )


def test_xml_is_valid_syntax():
    """Test that generated XML is syntactically valid"""
    invoice = _sample_invoice()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Try to parse XML - should not raise exception
    try:
        ET.fromstring(xml)
    except ET.ParseError as e:
        assert False, f"Generated XML is invalid: {e}"


def test_date_format_is_yyyymmdd():
    """Test that dates are formatted as YYYYMMDD (no hyphens)"""
    invoice = _sample_invoice()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Extract DATE tag
    date_match = re.search(r"<DATE>(.*?)</DATE>", xml)
    assert date_match, "DATE tag should be present"
    
    date_str = date_match.group(1)
    
    # Should be YYYYMMDD format (8 digits, no hyphens)
    assert len(date_str) == 8, f"Date should be 8 digits (YYYYMMDD), got '{date_str}'"
    assert date_str.isdigit(), f"Date should contain only digits, got '{date_str}'"
    assert "-" not in date_str, f"Date should not contain hyphens, got '{date_str}'"


def test_purchase_voucher_has_correct_vchtype():
    """Test that purchase vouchers have VCHTYPE='Purchase'"""
    invoice = _sample_invoice()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Extract VCHTYPE
    vchtype_match = re.search(r'<VCHTYPE>(.*?)</VCHTYPE>', xml)
    assert vchtype_match, "VCHTYPE should be present"
    
    vchtype = vchtype_match.group(1)
    assert vchtype == "Purchase", f"VCHTYPE should be 'Purchase' for purchase vouchers, got '{vchtype}'"


def test_sales_voucher_has_correct_vchtype():
    """Test that sales vouchers have VCHTYPE='Sales'"""
    invoice = _sample_invoice()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Sales", company_state_code=COMPANY_STATE_CODE
    )

    # Extract VCHTYPE
    vchtype_match = re.search(r'<VCHTYPE>(.*?)</VCHTYPE>', xml)
    assert vchtype_match, "VCHTYPE should be present"
    
    vchtype = vchtype_match.group(1)
    assert vchtype == "Sales", f"VCHTYPE should be 'Sales' for sales vouchers, got '{vchtype}'"


def test_sign_conventions_correct():
    """Test that sign conventions are correct (debits positive, credits negative)"""
    invoice = _sample_invoice()
    xml = invoice_to_tally_xml(
        invoice, voucher_type="Purchase", company_state_code=COMPANY_STATE_CODE
    )

    # Extract all ledger entries
    entries = re.findall(
        r"<ALLLEDGERENTRIES\.LIST>(.*?)</ALLLEDGERENTRIES\.LIST>", xml, re.DOTALL
    )

    for entry in entries:
        m_amount = re.search(r"<AMOUNT>([-0-9\.]+)</AMOUNT>", entry)
        m_deemed = re.search(r"<ISDEEMEDPOSITIVE>(Yes|No)</ISDEEMEDPOSITIVE>", entry)
        
        if not m_amount or not m_deemed:
            continue
            
        amount = float(m_amount.group(1))
        is_deemed_positive = m_deemed.group(1) == "Yes"
        
        # Debits: ISDEEMEDPOSITIVE=No, amount should be positive
        # Credits: ISDEEMEDPOSITIVE=Yes, amount should be negative
        if is_deemed_positive:
            assert amount < 0, f"Credit entry should have negative amount, got {amount}"
        else:
            assert amount > 0, f"Debit entry should have positive amount, got {amount}"

