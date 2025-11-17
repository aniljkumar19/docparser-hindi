import csv
from io import StringIO
from typing import Dict, Any

def invoice_to_tally_csv(parsed: Dict[str, Any]) -> str:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["Date","Invoice Number","Party Name","GSTIN","Item","Qty","Rate","Amount","CGST","SGST","IGST","Total"])
    inv_no = (parsed.get("invoice_number") or {}).get("value") if isinstance(parsed.get("invoice_number"), dict) else parsed.get("invoice_number")
    date = (parsed.get("date") or {}).get("value") if isinstance(parsed.get("date"), dict) else parsed.get("date")
    party = (parsed.get("buyer") or {}).get("name") or ""
    gstin = (parsed.get("buyer") or {}).get("gstin") or ""
    cgst = sum(t.get("amount",0) for t in parsed.get("taxes",[]) if t.get("type")=="CGST")
    sgst = sum(t.get("amount",0) for t in parsed.get("taxes",[]) if t.get("type")=="SGST")
    igst = sum(t.get("amount",0) for t in parsed.get("taxes",[]) if t.get("type")=="IGST")
    total = parsed.get("total") or 0
    for li in parsed.get("line_items",[]):
        w.writerow([date, inv_no, party, gstin, li.get("desc",""), li.get("qty",0), li.get("unit_price",0), li.get("amount",0), cgst, sgst, igst, total])
    return buf.getvalue()
