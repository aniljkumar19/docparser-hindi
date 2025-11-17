import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.parsers.detect import detect_doc_type_with_scores


def test_detect_prefers_gstr_over_bank_when_gstr_hints_present():
    sample_text = """
    FORM GSTR-3B
    GSTN: 27ABCDE1234F1Z5
    Summary of outward supplies and inward supplies liable to reverse charge
    Taxable value 125000.00
    Bank name : HDFC Bank
    """
    doc_type, scores, _ = detect_doc_type_with_scores(sample_text)
    assert doc_type == "gstr"
    assert scores["gstr"] >= scores["bank_statement"]

