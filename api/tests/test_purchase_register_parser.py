import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.parsers.purchase_register import (
    normalize_purchase_register,
    purchase_register_total_taxable,
)


def test_purchase_register_csv_sample():
    sample = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "purchase_register"
        / "sample.csv"
    )
    raw = sample.read_text(encoding="utf-8")
    parsed = normalize_purchase_register(raw)

    assert parsed["doc_type"] == "purchase_register"
    assert parsed["warnings"] == []
    entries = parsed["entries"]
    assert len(entries) == 3

    first = entries[0]
    assert first["invoice_number"] == "PUR-001"
    assert first["taxable_value"] == 100000
    assert first["cgst"] == 9000
    assert first["sgst"] == 9000
    assert first["total_value"] == 118000

    pr = {"entries": entries}
    assert purchase_register_total_taxable(pr) == 160000.0

