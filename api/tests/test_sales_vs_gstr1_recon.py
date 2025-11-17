import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.recon.sales_vs_gstr1 import (
    total_from_sales_register,
    total_from_gstr1,
    reconcile_sales_register_vs_gstr1,
)


def _sample_sales_register():
    return {
        "entries": [
            {"taxable_value": 100000, "igst": 0, "cgst": 9000, "sgst": 9000, "total_value": 118000},
            {"taxable_value": 50000, "igst": 9000, "cgst": 0, "sgst": 0, "total_value": 59000},
            {"taxable_value": 10000, "igst": 0, "cgst": 900, "sgst": 900, "total_value": 11800},
        ]
    }


def _sample_gstr1():
    sample = Path(__file__).resolve().parent / "fixtures" / "gstr" / "gstr1_dummy.txt"
    raw = sample.read_text(encoding="utf-8")
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from app.parsers.gstr1 import normalize_gstr1

    return normalize_gstr1(raw)


def test_total_from_sales_register_and_gstr1_match():
    sr = _sample_sales_register()
    g1 = _sample_gstr1()
    sr_totals = total_from_sales_register(sr)
    g1_totals = total_from_gstr1(g1)
    assert sr_totals["taxable_value"] == g1_totals["taxable_value"] == 160000.0
    assert sr_totals["igst"] == g1_totals["igst"] == 9000.0
    assert sr_totals["cgst"] == g1_totals["cgst"] == 9900.0
    assert sr_totals["sgst"] == g1_totals["sgst"] == 9900.0


def test_reconcile_sales_register_vs_gstr1_matched():
    sr = _sample_sales_register()
    g1 = _sample_gstr1()
    rec = reconcile_sales_register_vs_gstr1(sr, g1, tolerance=1.0)
    assert rec["status"] == "matched"
    assert abs(rec["difference"]["total"]) <= 1.0


