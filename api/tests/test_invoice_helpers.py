import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.parsers.invoice_helpers import apply_invoice_fallbacks, evaluate_invoice_quality


def test_apply_invoice_fallbacks_fills_missing_fields():
    result = {"warnings": []}
    text = (
        "Bill Date\n15 Nov 2025\nSub Total\n20,000.01\nCGST@6%\n1,200.00\nSGST@6%\n1,200.00\n"
        "Tax Invoice No: 13-123\nTotal Rs.\n22,400.01"
    )
    enriched = apply_invoice_fallbacks(result, text)

    assert enriched["invoice_number"] == "13-123"
    assert enriched["date"] == "2025-11-15"
    assert enriched["subtotal"] == 20000.01
    assert enriched["total"] == 22400.01
    assert len(enriched["taxes"]) == 2


def test_evaluate_invoice_quality_marks_low_coverage():
    result = {
        "invoice_number": None,
        "date": None,
        "seller": {"gstin": None},
        "buyer": {"gstin": None},
        "subtotal": None,
        "taxes": [],
        "total": None,
    }
    quality = evaluate_invoice_quality(result)
    assert quality["is_usable"] is False
    assert "missing_invoice_number" in quality["issues"]


def test_evaluate_invoice_quality_marks_usable():
    result = {
        "invoice_number": "13-123",
        "date": "2025-11-15",
        "seller": {"gstin": "27ABCDE1234F2Z5"},
        "buyer": {"gstin": "27ABCDE1234F2Z6"},
        "subtotal": 20000.0,
        "taxes": [{"type": "CGST", "amount": 1200}],
        "total": None,
    }
    quality = evaluate_invoice_quality(result)
    assert quality["is_usable"] is True

