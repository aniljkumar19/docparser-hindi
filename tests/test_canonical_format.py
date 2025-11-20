"""
Tests for Canonical JSON Format v0.1 conversion
"""

import pytest
import json
from api.app.parsers.canonical import normalize_to_canonical


def test_invoice_to_canonical():
    """Test invoice conversion to canonical format."""
    invoice = {
        "invoice_number": "INV-001",
        "date": "2025-01-15",
        "seller": {"name": "ABC Corp", "gstin": "27ABCDE1234F1Z5"},
        "buyer": {"name": "XYZ Ltd", "gstin": "24XYZ9876543Z1B3"},
        "items": [
            {
                "description": "Product A",
                "quantity": 10,
                "unit_price": 10000,
                "amount": 100000,
                "tax_rate": 18.0,
                "tax_amount": 18000
            }
        ],
        "tax_breakup": {
            "cgst": 9000,
            "sgst": 9000,
            "igst": 0,
            "cess": 0
        },
        "totals": {
            "subtotal": 100000,
            "tax_total": 18000,
            "grand_total": 118000,
            "currency": "INR"
        }
    }
    
    canonical = normalize_to_canonical("invoice", invoice)
    
    # Check top-level structure
    assert canonical["schema_version"] == "doc.v0.1"
    assert canonical["doc_type"] == "invoice"
    assert canonical["doc_id"].startswith("invoice-")
    assert canonical["doc_date"] == "2025-01-15"
    assert canonical["period"] is None
    
    # Check business/parties
    assert canonical["business"]["gstin"] == "27ABCDE1234F1Z5"
    assert canonical["parties"]["primary"]["name"] == "ABC Corp"
    assert canonical["parties"]["counterparty"]["name"] == "XYZ Ltd"
    
    # Check financials
    assert canonical["financials"]["currency"] == "INR"
    assert canonical["financials"]["subtotal"] == 100000.0
    assert canonical["financials"]["tax_breakup"]["cgst"] == 9000.0
    assert canonical["financials"]["grand_total"] == 118000.0
    
    # Check entries
    assert len(canonical["entries"]) == 1
    entry = canonical["entries"][0]
    assert entry["entry_type"] == "invoice"
    assert entry["entry_number"] == "INV-001"
    assert len(entry["line_items"]) == 1
    assert entry["line_items"][0]["description"] == "Product A"


def test_purchase_register_to_canonical():
    """Test purchase register conversion to canonical format."""
    purchase_register = {
        "doc_type": "purchase_register",
        "gstin_of_business": "27ABCDE1234F1Z5",
        "period": "2025-01",
        "entries": [
            {
                "invoice_number": "PUR-001",
                "invoice_date": "2025-01-05",
                "supplier_name": "XYZ Distributors",
                "supplier_gstin": "27XYZ9876543Z1B3",
                "taxable_value": 100000.00,
                "cgst": 9000.00,
                "sgst": 9000.00,
                "igst": 0.00,
                "cess": 0.00,
                "total_value": 118000.00,
                "reverse_charge": False,
                "invoice_type": "REGULAR"
            },
            {
                "invoice_number": "PUR-002",
                "invoice_date": "2025-01-10",
                "supplier_name": "ABC Suppliers",
                "supplier_gstin": "24ABC1234567Z1C2",
                "taxable_value": 50000.00,
                "cgst": 0.00,
                "sgst": 0.00,
                "igst": 9000.00,
                "cess": 0.00,
                "total_value": 59000.00,
                "reverse_charge": False,
                "invoice_type": "REGULAR"
            }
        ],
        "warnings": []
    }
    
    canonical = normalize_to_canonical("purchase_register", purchase_register)
    
    # Check structure
    assert canonical["schema_version"] == "doc.v0.1"
    assert canonical["doc_type"] == "purchase_register"
    assert canonical["period"] == "2025-01"
    assert canonical["doc_date"] is None
    
    # Check business
    assert canonical["business"]["gstin"] == "27ABCDE1234F1Z5"
    assert canonical["business"]["state_code"] == "27"
    
    # Check financials (aggregated)
    assert canonical["financials"]["subtotal"] == 150000.0  # 100000 + 50000
    assert canonical["financials"]["tax_breakup"]["cgst"] == 9000.0
    assert canonical["financials"]["tax_breakup"]["sgst"] == 9000.0
    assert canonical["financials"]["tax_breakup"]["igst"] == 9000.0
    assert canonical["financials"]["grand_total"] == 177000.0  # 118000 + 59000
    
    # Check entries
    assert len(canonical["entries"]) == 2
    entry1 = canonical["entries"][0]
    assert entry1["entry_type"] == "register_entry"
    assert entry1["entry_number"] == "PUR-001"
    assert entry1["party"]["name"] == "XYZ Distributors"
    assert entry1["party"]["state_code"] == "27"
    assert entry1["amounts"]["taxable_value"] == 100000.0
    
    entry2 = canonical["entries"][1]
    assert entry2["entry_number"] == "PUR-002"
    assert entry2["party"]["state_code"] == "24"  # Different state → IGST
    assert entry2["amounts"]["tax_breakup"]["igst"] == 9000.0
    
    # Check doc_specific
    assert canonical["doc_specific"]["total_invoices"] == 2
    assert canonical["doc_specific"]["total_suppliers"] == 2


def test_invoice_with_taxes_array():
    """Test invoice with taxes array (not tax_breakup object)."""
    invoice = {
        "invoice_number": "INV-002",
        "date": "2025-01-20",
        "seller": {"gstin": "27ABCDE1234F1Z5"},
        "buyer": {"gstin": "24XYZ9876543Z1B3"},
        "subtotal": 50000,
        "total": 59000,
        "taxes": [
            {"type": "CGST", "amount": 4500},
            {"type": "SGST", "amount": 4500}
        ],
        "line_items": [
            {"desc": "Item 1", "qty": 1, "unit_price": 50000, "amount": 50000}
        ]
    }
    
    canonical = normalize_to_canonical("invoice", invoice)
    
    # Should convert taxes array to tax_breakup
    assert canonical["financials"]["tax_breakup"]["cgst"] == 4500.0
    assert canonical["financials"]["tax_breakup"]["sgst"] == 4500.0
    assert canonical["financials"]["tax_total"] == 9000.0


def test_sales_register_to_canonical():
    """Test sales register conversion to canonical format."""
    import json
    import os
    
    # Try to load from fixture file
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "sales_register.json")
    if os.path.exists(fixture_path):
        with open(fixture_path, "r") as f:
            sales_register = json.load(f)
    else:
        # Fallback to inline data
        sales_register = {
            "doc_type": "sales_register",
            "gstin_of_business": "27ABCDE1234F1Z5",
            "period": "2025-01",
            "entries": [
                {
                    "invoice_number": "SAL-001",
                    "invoice_date": "2025-01-05",
                    "customer_name": "Customer A",
                    "customer_gstin": "27CUST1234567Z1D2",
                    "taxable_value": 200000.00,
                    "cgst": 18000.00,
                    "sgst": 18000.00,
                    "igst": 0.00,
                    "total_value": 236000.00
                }
            ]
        }
    
    canonical = normalize_to_canonical("sales_register", sales_register)
    
    # Check structure
    assert canonical["schema_version"] == "doc.v0.1"
    assert canonical["doc_type"] == "sales_register"
    assert canonical["period"] == "2025-01"
    assert canonical["doc_date"] is None
    
    # Check business
    assert canonical["business"]["gstin"] == "27ABCDE1234F1Z5"
    assert canonical["business"]["state_code"] == "27"
    
    # Check financials (aggregated)
    assert canonical["financials"]["subtotal"] > 0
    assert "tax_breakup" in canonical["financials"]
    
    # Check entries
    assert len(canonical["entries"]) == len(sales_register["entries"])
    entry = canonical["entries"][0]
    assert entry["entry_type"] == "register_entry"
    assert entry["party"]["name"] == "Customer A"
    assert entry["party"]["state_code"] == "27"
    
    # Check doc_specific
    assert canonical["doc_specific"]["total_invoices"] == len(sales_register["entries"])
    assert canonical["doc_specific"]["total_customers"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

