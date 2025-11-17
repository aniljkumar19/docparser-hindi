import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.parsers.gst_invoice import parse_text_rules


def test_gst_invoice_parser_extracts_gstin_and_invoice():
    sample_text = """
    TAX INVOICE
    Invoice No: 13-123
    Seller GSTIN: 27ABCDE1234F2Z5
    Buyer GSTIN: 29ABCDE1234F2Z6
    Total Rs. 22400.01
    """
    parsed = parse_text_rules(sample_text)
    assert parsed["doc_type"] == "gst_invoice"
    assert parsed.get("seller", {}).get("gstin") == "27ABCDE1234F2Z5"
    assert parsed.get("buyer", {}).get("gstin") == "29ABCDE1234F2Z6"
    assert parsed.get("invoice_number", {}).get("value") == "13-123"

