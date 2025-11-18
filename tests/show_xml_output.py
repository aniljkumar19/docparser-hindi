#!/usr/bin/env python3
"""Show XML output snippets to verify GST auto-fix"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from app.exporters.tally_xml import invoice_to_tally_xml

# Purchase 1: Same state (27) - has IGST, should convert to CGST+SGST
purchase1 = {
    'invoice_number': 'TEST-001',
    'date': '2025-01-15',
    'buyer': {'name': 'Intra Supplier', 'gstin': '27ABCDEF1234Z1A2'},
    'subtotal': 10000,
    'total': 11800,
    'igst': 1800,
    'taxes': [{'type': 'IGST', 'amount': 1800}],
    'line_items': [{'desc': 'Test Item', 'qty': 1, 'unit_price': 10000, 'amount': 10000}]
}

# Purchase 2: Different state (24) - has CGST+SGST, should convert to IGST
purchase2 = {
    'invoice_number': 'TEST-002',
    'date': '2025-01-16',
    'buyer': {'name': 'Inter Supplier', 'gstin': '24XYZ9876543Z1B3'},
    'subtotal': 20000,
    'total': 23600,
    'cgst': 1800,
    'sgst': 1800,
    'taxes': [{'type': 'CGST', 'amount': 1800}, {'type': 'SGST', 'amount': 1800}],
    'line_items': [{'desc': 'Test Item', 'qty': 1, 'unit_price': 20000, 'amount': 20000}]
}

print("=" * 70)
print("Purchase 1: Same State (27) - IGST converted to CGST+SGST")
print("=" * 70)
xml1 = invoice_to_tally_xml(purchase1, voucher_type='Purchase', company_state_code='27')
# Extract ledger entries section
start = xml1.find('<ALLLEDGERENTRIES.LIST>')
end = xml1.find('</VOUCHER>')
if start >= 0 and end > start:
    print(xml1[start:end])
else:
    # Show a snippet
    lines = xml1.split('\n')
    for line in lines:
        if 'CGST' in line or 'SGST' in line or 'IGST' in line or 'LEDGERNAME' in line:
            print(line.strip())

print("\n" + "=" * 70)
print("Purchase 2: Different State (24) - CGST+SGST converted to IGST")
print("=" * 70)
xml2 = invoice_to_tally_xml(purchase2, voucher_type='Purchase', company_state_code='27')
# Extract ledger entries section
start = xml2.find('<ALLLEDGERENTRIES.LIST>')
end = xml2.find('</VOUCHER>')
if start >= 0 and end > start:
    print(xml2[start:end])
else:
    # Show a snippet
    lines = xml2.split('\n')
    for line in lines:
        if 'CGST' in line or 'SGST' in line or 'IGST' in line or 'LEDGERNAME' in line:
            print(line.strip())

