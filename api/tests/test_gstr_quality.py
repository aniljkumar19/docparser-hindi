import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.parsers.gstr import gstr_quality_score


def test_gstr_quality_score_low_for_sparse_result():
    parsed = {
        "gstr_form": None,
        "period": None,
        "turnover": None,
        "taxable_value": None,
        "taxes": [],
        "invoices": [],
    }
    assert gstr_quality_score(parsed) == 0


def test_gstr_quality_score_high_with_data():
    parsed = {
        "gstr_form": {"value": "GSTR-3B"},
        "period": {"value": "11-2024"},
        "turnover": {"value": 100000},
        "taxable_value": {"value": 90000},
        "taxes": [{"type": "IGST", "amount": 1000}],
        "invoices": [{"invoice_number": "INV-1"}],
    }
    assert gstr_quality_score(parsed) >= 5

