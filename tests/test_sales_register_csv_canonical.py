"""
Test canonical format conversion for sales register CSV data
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app.parsers.canonical import normalize_to_canonical


def test_sales_register_csv_to_canonical():
    """Test converting sales register CSV data to canonical format."""
    
    # Simulate what the parser would produce from the CSV
    sales_register = {
        "doc_type": "sales_register",
        "gstin_of_business": "27ABCDE1234F1Z5",  # Assuming company GSTIN
        "period": "2025-11",
        "entries": [
            {
                "invoice_number": "INV-001",
                "invoice_date": "2025-11-05",
                "customer_name": "ABC DISTRIBUTORS",
                "customer_gstin": "27ABCDEF1234Z5",
                "place_of_supply": "27-Maharashtra",
                "reverse_charge": False,
                "invoice_type": "REGULAR",
                "taxable_value": 100000.00,
                "cgst": 9000.00,
                "sgst": 9000.00,
                "igst": 0.00,
                "cess": 0.00,
                "total_value": 118000.00,
                "hsn_summary": []
            },
            {
                "invoice_number": "INV-002",
                "invoice_date": "2025-11-10",
                "customer_name": "XYZ STORES",
                "customer_gstin": "29XYZSTO1234Z9",
                "place_of_supply": "29-Karnataka",
                "reverse_charge": False,
                "invoice_type": "REGULAR",
                "taxable_value": 50000.00,
                "cgst": 0.00,
                "sgst": 0.00,
                "igst": 9000.00,
                "cess": 0.00,
                "total_value": 59000.00,
                "hsn_summary": []
            },
            {
                "invoice_number": "INV-003",
                "invoice_date": "2025-11-20",
                "customer_name": "QWER INDUSTRIES",
                "customer_gstin": "27QWERIN1234Z8",
                "place_of_supply": "27-Maharashtra",
                "reverse_charge": False,
                "invoice_type": "REGULAR",
                "taxable_value": 10000.00,
                "cgst": 900.00,
                "sgst": 900.00,
                "igst": 0.00,
                "cess": 0.00,
                "total_value": 11800.00,
                "hsn_summary": []
            }
        ],
        "warnings": [],
        "meta": {
            "parser_version": "sales_register_v1"
        }
    }
    
    # Convert to canonical format
    canonical = normalize_to_canonical("sales_register", sales_register)
    
    # Print the result
    print("\n" + "="*80)
    print("SALES REGISTER → CANONICAL FORMAT CONVERSION")
    print("="*80)
    print(json.dumps(canonical, indent=2))
    print("="*80)
    
    # Validate structure
    assert canonical["schema_version"] == "doc.v0.1"
    assert canonical["doc_type"] == "sales_register"
    assert canonical["period"] == "2025-11"
    
    # Check business
    assert canonical["business"]["gstin"] == "27ABCDE1234F1Z5"
    assert canonical["business"]["state_code"] == "27"
    
    # Check financials (aggregated)
    expected_subtotal = 100000 + 50000 + 10000  # 160000
    expected_tax_total = (9000 + 9000) + 9000 + (900 + 900)  # 18000 + 9000 + 1800 = 28800
    expected_grand_total = 118000 + 59000 + 11800  # 188800
    
    assert canonical["financials"]["subtotal"] == expected_subtotal
    assert canonical["financials"]["tax_total"] == expected_tax_total
    assert canonical["financials"]["grand_total"] == expected_grand_total
    
    # Check entries
    assert len(canonical["entries"]) == 3
    
    # Entry 1: Same state (27) - should have CGST+SGST
    entry1 = canonical["entries"][0]
    assert entry1["entry_number"] == "INV-001"
    assert entry1["party"]["name"] == "ABC DISTRIBUTORS"
    assert entry1["party"]["state_code"] == "27"
    assert entry1["amounts"]["tax_breakup"]["cgst"] == 9000.0
    assert entry1["amounts"]["tax_breakup"]["sgst"] == 9000.0
    assert entry1["amounts"]["tax_breakup"]["igst"] == 0.0
    
    # Entry 2: Different state (29) - should have IGST
    entry2 = canonical["entries"][1]
    assert entry2["entry_number"] == "INV-002"
    assert entry2["party"]["name"] == "XYZ STORES"
    assert entry2["party"]["state_code"] == "29"
    assert entry2["amounts"]["tax_breakup"]["cgst"] == 0.0
    assert entry2["amounts"]["tax_breakup"]["sgst"] == 0.0
    assert entry2["amounts"]["tax_breakup"]["igst"] == 9000.0
    
    # Entry 3: Same state (27) - should have CGST+SGST
    entry3 = canonical["entries"][2]
    assert entry3["entry_number"] == "INV-003"
    assert entry3["party"]["name"] == "QWER INDUSTRIES"
    assert entry3["party"]["state_code"] == "27"
    assert entry3["amounts"]["tax_breakup"]["cgst"] == 900.0
    assert entry3["amounts"]["tax_breakup"]["sgst"] == 900.0
    assert entry3["amounts"]["tax_breakup"]["igst"] == 0.0
    
    # Check doc_specific
    assert canonical["doc_specific"]["total_invoices"] == 3
    assert canonical["doc_specific"]["total_customers"] == 3
    
    print("\n✅ All validations passed!")
    print(f"   Total invoices: {canonical['doc_specific']['total_invoices']}")
    print(f"   Total customers: {canonical['doc_specific']['total_customers']}")
    print(f"   Grand total: ₹{canonical['financials']['grand_total']:,.2f}")
    
    return canonical


if __name__ == "__main__":
    result = test_sales_register_csv_to_canonical()

