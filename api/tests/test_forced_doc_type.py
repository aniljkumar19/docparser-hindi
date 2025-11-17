import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.parsers.router import parse_any


def test_forced_gst_invoice_routes_to_gst_invoice():
    data = b"FORM GSTR-3B\nGSTN: 27ABCDE1234F1Z5\nSummary of outward supplies"
    result, meta = parse_any("sample.txt", data, forced_doc_type="gst_invoice")

    assert meta.get("doc_type_forced") is True
    assert meta.get("detected_doc_type") == "gst_invoice"
    assert meta.get("doc_type_internal") == "gst_invoice"
    # ensure parser returns structure (even if minimal)
    assert isinstance(result, dict)

