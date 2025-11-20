#!/usr/bin/env python3
"""
Block 1 Testing Script: Validators + ITC Reconciliation

Tests:
- Sales Register validation
- GSTR-2B validation
- GSTR-3B validation
- ITC 2B vs 3B reconciliation

Run: python dev_test_block1.py
"""

import sys
from pathlib import Path

# Add api directory to path
sys.path.insert(0, str(Path(__file__).parent / "api"))

from app.validators.sales_register_validator import validate_sales_register
from app.validators.gstr2b_validator import validate_gstr2b
from app.validators.gstr3b_validator import validate_gstr3b
from app.recon.itc_2b_3b import reconcile_itc_2b_3b
from pprint import pprint

# === Paste your canonical JSON samples here ===

sales_register_doc = {
    "schema_version": "doc.v0.1",
    "doc_type": "sales_register",
    "doc_id": "sales_register-20251119225749",
    "doc_date": None,
    "period": None,
    "metadata": {
        "source_format": "sales_register",
        "parser_version": "sales_register_v1",
        "warnings": []
    },
    "business": {
        "name": None,
        "gstin": None,
        "state_code": None
    },
    "parties": {
        "primary": {
            "name": None,
            "gstin": None,
            "state_code": None
        }
    },
    "financials": {
        "currency": "INR",
        "subtotal": 160000,
        "tax_breakup": {
            "cgst": 9900,
            "sgst": 9900,
            "igst": 9000,
            "cess": 0
        },
        "tax_total": 28800,
        "grand_total": 188800
    },
    "entries": [
        {
            "entry_id": "entry-1",
            "entry_type": "register_entry",
            "entry_date": "2025-11-05",
            "entry_number": "INV-001",
            "party": {
                "name": "ABC DISTRIBUTORS",
                "gstin": "27ABCDEF1234Z5",
                "state_code": "27"
            },
            "amounts": {
                "taxable_value": 100000,
                "tax_breakup": {
                    "cgst": 9000,
                    "sgst": 9000,
                    "igst": 0,
                    "cess": 0
                },
                "total": 118000
            },
            "line_items": [],
            "doc_specific": {
                "reverse_charge": False,
                "invoice_type": "REGULAR",
                "place_of_supply": "27-Maharashtra",
                "hsn_summary": []
            }
        },
        {
            "entry_id": "entry-2",
            "entry_type": "register_entry",
            "entry_date": "2025-11-10",
            "entry_number": "INV-002",
            "party": {
                "name": "XYZ STORES",
                "gstin": "29XYZSTO1234Z9",
                "state_code": "29"
            },
            "amounts": {
                "taxable_value": 50000,
                "tax_breakup": {
                    "cgst": 0,
                    "sgst": 0,
                    "igst": 9000,
                    "cess": 0
                },
                "total": 59000
            },
            "line_items": [],
            "doc_specific": {
                "reverse_charge": False,
                "invoice_type": "REGULAR",
                "place_of_supply": "29-Karnataka",
                "hsn_summary": []
            }
        },
        {
            "entry_id": "entry-3",
            "entry_type": "register_entry",
            "entry_date": "2025-11-20",
            "entry_number": "INV-003",
            "party": {
                "name": "QWER INDUSTRIES",
                "gstin": "27QWERIN1234Z8",
                "state_code": "27"
            },
            "amounts": {
                "taxable_value": 10000,
                "tax_breakup": {
                    "cgst": 900,
                    "sgst": 900,
                    "igst": 0,
                    "cess": 0
                },
                "total": 11800
            },
            "line_items": [],
            "doc_specific": {
                "reverse_charge": False,
                "invoice_type": "REGULAR",
                "place_of_supply": "27-Maharashtra",
                "hsn_summary": []
            }
        }
    ],
    "doc_specific": {
        "total_invoices": 3,
        "total_customers": 3
    }
}

gstr3b_doc = {
    "schema_version": "doc.v0.1",
    "doc_type": "gstr3b",
    "doc_id": "gstr3b-november-2025",
    "doc_date": None,
    "period": "November 2025",
    "metadata": {
        "source_format": "gstr3b",
        "parser_version": "gstr3b_v1",
        "warnings": []
    },
    "business": {
        "name": "ABC TRADERS PRIVATE LIMITED",
        "gstin": "27ABCDE1234F2Z5",
        "state_code": "27"
    },
    "parties": {
        "primary": {
            "name": "ABC TRADERS PRIVATE LIMITED",
            "gstin": "27ABCDE1234F2Z5",
            "state_code": "27"
        }
    },
    "financials": {
        "currency": "INR",
        "subtotal": 510000,
        "tax_breakup": {
            "cgst": 15000,
            "sgst": 15000,
            "igst": 500,
            "cess": 0
        },
        "tax_total": 30500,
        "grand_total": 540500
    },
    "entries": [
        {
            "entry_id": "gstr3b-outward-supplies",
            "entry_type": "gstr_entry",
            "entry_date": None,
            "entry_number": "OUTWARD",
            "party": None,
            "amounts": {
                "taxable_value": 500000,
                "tax_breakup": {
                    "cgst": 15000,
                    "sgst": 15000,
                    "igst": 0,
                    "cess": 0
                },
                "total": 530000
            },
            "line_items": [],
            "doc_specific": {
                "supply_type": "outward_taxable"
            }
        },
        {
            "entry_id": "gstr3b-reverse-charge",
            "entry_type": "gstr_entry",
            "entry_date": None,
            "entry_number": "REVERSE_CHARGE",
            "party": None,
            "amounts": {
                "taxable_value": 10000,
                "tax_breakup": {
                    "cgst": 0,
                    "sgst": 0,
                    "igst": 500,
                    "cess": 0
                },
                "total": 10500
            },
            "line_items": [],
            "doc_specific": {
                "supply_type": "reverse_charge_inward"
            }
        }
    ],
    "doc_specific": {
        "gstr_form": "GSTR-3B",
        "legal_name": "ABC TRADERS PRIVATE LIMITED",
        "trade_name": "ABC TRADERS",
        "outward_supplies": {
            "taxable_value": 500000,
            "cgst": 15000,
            "sgst": 15000,
            "igst": 0,
            "cess": 0
        },
        "reverse_charge_inward_supplies": {
            "taxable_value": 10000,
            "cgst": 0,
            "sgst": 0,
            "igst": 500,
            "cess": 0
        },
        "input_tax_credit": {
            "total": {
                "igst": 9000,
                "cgst": 10000,
                "sgst": 10000,
                "cess": 0
            }
        },
        "tax_payable": {
            "igst": 2500,
            "cgst": 5000,
            "sgst": 5000,
            "cess": 0
        },
        "tax_paid": {
            "through_itc": {
                "igst": 2500,
                "cgst": 5000,
                "sgst": 5000,
                "cess": 0
            },
            "in_cash": {
                "igst": 0,
                "cgst": 0,
                "sgst": 0,
                "cess": 0
            }
        },
        "exempt_nil_nongst_supplies": {
            "exempt": 0,
            "nil_rated": 0,
            "non_gst": 0
        },
        "verification": {
            "name": "Rajesh Kumar",
            "designation": "Authorized Signatory",
            "date": "2025-12-20",
            "place": "Mumbai"
        }
    }
}

gstr2b_doc = {
    "schema_version": "doc.v0.1",
    "doc_type": "gstr2b",
    "doc_id": "gstr2b-november-2025",
    "doc_date": None,
    "period": "November 2025",
    "metadata": {
        "source_format": "gstr2b",
        "parser_version": "gstr2b_v1",
        "warnings": []
    },
    "business": {
        "name": "ABC TRADERS PRIVATE LIMITED",
        "gstin": "27ABCDE1234F2Z5",
        "state_code": "27"
    },
    "parties": {
        "primary": {
            "name": "ABC TRADERS PRIVATE LIMITED",
            "gstin": "27ABCDE1234F2Z5",
            "state_code": "27"
        }
    },
    "financials": {
        "currency": "INR",
        "subtotal": 160000,
        "tax_breakup": {
            "cgst": 9900,
            "sgst": 9900,
            "igst": 9000,
            "cess": 0
        },
        "tax_total": 28800,
        "grand_total": 188800
    },
    "entries": [
        {
            "entry_id": "gstr2b-entry-1",
            "entry_type": "gstr2b_invoice",
            "entry_date": "2025-11-05",
            "entry_number": "INV-001",
            "party": {
                "name": "ABC DISTRIBUTORS",
                "gstin": "27ABCDEF1234Z5",
                "state_code": "27"
            },
            "amounts": {
                "taxable_value": 100000,
                "tax_breakup": {
                    "cgst": 9000,
                    "sgst": 9000,
                    "igst": 0,
                    "cess": 0
                },
                "total": 118000
            },
            "line_items": [],
            "doc_specific": {
                "section": "b2b",
                "place_of_supply": "27",
                "itc_availability": "availed",
                "reason": None
            }
        },
        {
            "entry_id": "gstr2b-entry-2",
            "entry_type": "gstr2b_invoice",
            "entry_date": "2025-11-10",
            "entry_number": "INV-002",
            "party": {
                "name": "XYZ STORES",
                "gstin": "29XYZSTO1234Z9",
                "state_code": "29"
            },
            "amounts": {
                "taxable_value": 50000,
                "tax_breakup": {
                    "cgst": 0,
                    "sgst": 0,
                    "igst": 9000,
                    "cess": 0
                },
                "total": 59000
            },
            "line_items": [],
            "doc_specific": {
                "section": "b2b",
                "place_of_supply": "29",
                "itc_availability": "availed",
                "reason": None
            }
        }
    ],
    "doc_specific": {
        "gstr_form": "GSTR-2B",
        "legal_name": "ABC TRADERS PRIVATE LIMITED",
        "trade_name": "ABC TRADERS",
        "summary": {
            "total_taxable_value": 160000,
            "total_igst": 9000,
            "total_cgst": 9900,
            "total_sgst": 9900,
            "total_cess": 0
        },
        "sections": {
            "b2b_count": 2
        }
    }
}


if __name__ == "__main__":
    print("=" * 60)
    print("Block 1 Testing: Validators + ITC Reconciliation")
    print("=" * 60)
    
    print("\n=== Sales Register Validation ===")
    sr_issues = validate_sales_register(sales_register_doc)
    print(f"Issues found: {len(sr_issues)}")
    if sr_issues:
        pprint(sr_issues)
    else:
        print("✅ No issues found - validation passed!")
    
    print("\n=== GSTR-2B Validation ===")
    gstr2b_issues = validate_gstr2b(gstr2b_doc)
    print(f"Issues found: {len(gstr2b_issues)}")
    if gstr2b_issues:
        pprint(gstr2b_issues)
    else:
        print("✅ No issues found - validation passed!")
    
    print("\n=== GSTR-3B Validation ===")
    gstr3b_issues = validate_gstr3b(gstr3b_doc)
    print(f"Issues found: {len(gstr3b_issues)}")
    if gstr3b_issues:
        pprint(gstr3b_issues)
    else:
        print("✅ No issues found - validation passed!")
    
    print("\n=== ITC 2B vs 3B Reconciliation ===")
    rec = reconcile_itc_2b_3b(gstr2b_doc, gstr3b_doc)
    
    print(f"\nGSTIN: {rec['gstin']}")
    print(f"Period: {rec['period']}")
    print(f"\nOverall Status: {rec['overall']['status']}")
    print(f"  Available (2B): ₹{rec['overall']['total_available_2b']:,.2f}")
    print(f"  Claimed (3B):   ₹{rec['overall']['total_claimed_3b']:,.2f}")
    print(f"  Difference:     ₹{rec['overall']['difference']:,.2f}")
    
    print("\nBy Tax Head:")
    for head, data in rec['by_head'].items():
        status_icon = "✅" if data['status'] == "match" else "⚠️" if data['status'] == "over_claimed" else "🔻"
        print(f"  {head.upper()}: {status_icon} {data['status']}")
        print(f"    Available: ₹{data['available_2b']:,.2f}")
        print(f"    Claimed:   ₹{data['claimed_3b']:,.2f}")
        print(f"    Difference: ₹{data['difference']:,.2f}")
    
    print(f"\nIssues: {len(rec['issues'])}")
    if rec['issues']:
        for issue in rec['issues']:
            level_icon = "❌" if issue['level'] == "error" else "⚠️"
            print(f"  {level_icon} [{issue['level']}] {issue['code']}: {issue['message']}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

