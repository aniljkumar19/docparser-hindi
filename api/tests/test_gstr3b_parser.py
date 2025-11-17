import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.parsers.gstr3b import normalize_gstr3b


def test_gstr3b_parser_sample():
    sample_text = Path(__file__).resolve().parent / "fixtures" / "gstr" / "gstr3b_dummy.txt"
    raw_text = sample_text.read_text(encoding="utf-8")
    parsed = normalize_gstr3b(raw_text)

    assert parsed["gstin"] == "27ABCDE1234F2Z5"
    assert parsed["period"]["month"] == 11
    assert parsed["period"]["year"] == 2025
    assert parsed["period"]["label"] == "November 2025"
    assert parsed["outward_supplies"]["taxable_value"] == 500000.00
    assert parsed["tax_payable"]["cgst"] == 5000.00

