import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.recon.purchase_vs_gstr3b import (
    total_itc_from_purchase_register,
    reconcile_pr_vs_gstr3b_itc,
)


def _sample_purchase_register():
    return {
        "entries": [
            {"igst": 0.0, "cgst": 9000.0, "sgst": 9000.0},
            {"igst": 9000.0, "cgst": 0.0, "sgst": 0.0},
            {"igst": 0.0, "cgst": 900.0, "sgst": 900.0},
        ]
    }


def _sample_gstr3b():
    return {
        "input_tax_credit": {
            "total": {
                "igst": 9000.0,
                "cgst": 9900.0,
                "sgst": 9900.0,
            }
        }
    }


def test_total_itc_from_purchase_register():
    pr = _sample_purchase_register()
    totals = total_itc_from_purchase_register(pr)
    assert totals == {"igst": 9000.0, "cgst": 9900.0, "sgst": 9900.0, "total": 28800.0}


def test_reconcile_pr_vs_gstr3b_itc_matched():
    pr = _sample_purchase_register()
    g3b = _sample_gstr3b()
    report = reconcile_pr_vs_gstr3b_itc(pr, g3b, tolerance=0.5)
    assert report["status"] == "matched"
    assert report["difference"]["total"] == 0.0


def test_reconcile_pr_vs_gstr3b_itc_underclaimed():
    pr = _sample_purchase_register()
    g3b = _sample_gstr3b()
    g3b["input_tax_credit"]["total"]["igst"] = 10000.0  # 1k higher
    report = reconcile_pr_vs_gstr3b_itc(pr, g3b, tolerance=10.0)
    assert report["status"] == "itc_underclaimed"
    assert report["difference"]["igst"] == -1000.0


def test_reconcile_pr_vs_gstr3b_itc_overclaimed():
    pr = _sample_purchase_register()
    g3b = _sample_gstr3b()
    g3b["input_tax_credit"]["total"]["cgst"] = 8000.0  # 1.9k lower
    report = reconcile_pr_vs_gstr3b_itc(pr, g3b, tolerance=10.0)
    assert report["status"] == "itc_overclaimed"
    assert report["difference"]["cgst"] == 1900.0

