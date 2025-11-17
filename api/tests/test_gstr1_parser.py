import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.parsers.common import extract_text_with_layout
from app.parsers.gstr1 import normalize_gstr1, gstr1_outward_totals


def test_gstr1_parser_basic_parse():
    sample = Path(__file__).resolve().parent / "fixtures" / "gstr" / "gstr1_dummy.txt"
    raw = sample.read_text(encoding="utf-8")
    parsed = normalize_gstr1(raw)

    assert parsed["gstin"] == "27ABCDE1234F2Z5"
    assert parsed["period"]["month"] == 11
    assert parsed["period"]["year"] == 2025
    assert parsed["period"]["label"] == "November 2025"
    assert parsed["b2b_invoices"]
    first = parsed["b2b_invoices"][0]
    assert first["invoice_number"] == "INV-001"
    assert first["taxable_value"] == 100000.0


def test_gstr1_pdf_golden():
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "gstr"
    pdf_bytes = (fixtures_dir / "GSTR1.pdf").read_bytes()
    text = extract_text_with_layout(pdf_bytes)
    assert text
    parsed = normalize_gstr1(text)

    expected = json.loads((fixtures_dir / "gstr1_expected.json").read_text(encoding="utf-8"))

    assert parsed["gstin"] == expected["gstin"]
    assert len(parsed["b2b_invoices"]) == len(expected["b2b_invoices"]) == 3
    assert parsed["b2b_invoices"][0]["invoice_number"] == "INV-001"
    assert parsed["b2b_invoices"] == expected["b2b_invoices"]
    assert gstr1_outward_totals(parsed) == 160000.0

