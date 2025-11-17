from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _detect_delimiter(line: str) -> str:
    if "," in line:
        return ","
    if "\t" in line:
        return "\t"
    if ";" in line:
        return ";"
    return "spaces"


def _split_row(line: str, delimiter: str) -> List[str]:
    line = line.rstrip("\r\n")
    if delimiter == "spaces":
        return [p for p in re.split(r"\s{2,}", line.strip()) if p]
    return [p.strip() for p in line.split(delimiter) if p.strip()]


def _normalize_header(h: str) -> str:
    h = h.lower().strip()
    h = re.sub(r"[ ._/-]+", "", h)
    return h


def _parse_amount(val: str) -> float:
    if not val:
        return 0.0
    try:
        return float(val.replace(",", "").strip())
    except Exception:
        return 0.0


def _parse_date(val: str) -> Optional[str]:
    val = val.strip()
    m = re.match(r"(\d{2})[-/](\d{2})[-/](\d{4})", val)
    if m:
        d, mth, y = m.groups()
        return f"{y}-{mth}-{d}"
    return None


def _map_headers(header_cells: List[str]) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    for idx, cell in enumerate(header_cells):
        n = _normalize_header(cell)
        if n in {"invoicedate", "billdate", "date"}:
            mapping[idx] = "invoice_date"
        elif n in {"invoiceno", "billno", "invoicenumber"}:
            mapping[idx] = "invoice_number"
        elif n in {"customername", "buyername", "partyname"}:
            mapping[idx] = "customer_name"
        elif n in {"customergstin", "buyergstin", "gstin", "partygstin"}:
            mapping[idx] = "customer_gstin"
        elif n in {"placeofsupply", "pos"}:
            mapping[idx] = "place_of_supply"
        elif n in {"reversecharge", "rcm"}:
            mapping[idx] = "reverse_charge"
        elif n in {"invoicetype", "type"}:
            mapping[idx] = "invoice_type"
        elif n in {"taxablevalue", "taxableamount", "taxable"}:
            mapping[idx] = "taxable_value"
        elif n in {"igst", "igstamount"}:
            mapping[idx] = "igst"
        elif n in {"cgst", "cgstamount"}:
            mapping[idx] = "cgst"
        elif n in {"sgst", "sgstamount"}:
            mapping[idx] = "sgst"
        elif n in {"cess"}:
            mapping[idx] = "cess"
        elif n in {"invoicevalue", "totalvalue", "total"}:
            mapping[idx] = "total_value"
    return mapping


def normalize_sales_register(raw_text: str) -> Dict[str, Any]:
    lines: List[str] = []
    for ln in raw_text.splitlines():
        stripped = ln.strip()
        if not stripped:
            continue
        if re.match(r"^page\s+\d+\s+of\s+\d+", stripped.lower()):
            continue
        if re.match(r"^-{5,}$", stripped):
            continue
        lines.append(ln)

    warnings: List[str] = []
    if not lines:
        return {
            "doc_type": "sales_register",
            "gstin_of_business": None,
            "period": None,
            "entries": [],
            "warnings": ["empty_document"],
            "meta": {"parser_version": "sales_register_v1"},
        }

    header_idx = None
    for i, ln in enumerate(lines):
        if "invoice date" in ln.lower() and "invoice" in ln.lower():
            header_idx = i
            break
    if header_idx is None:
        warnings.append("header_not_found")
        header_idx = 0

    header_line = lines[header_idx]
    delimiter = _detect_delimiter(header_line)
    header_cells = _split_row(header_line, delimiter)
    mapping = _map_headers(header_cells)
    if not mapping:
        warnings.append("no_known_columns_found")

    entries: List[Dict[str, Any]] = []
    data_start = header_idx + 1
    date_re = re.compile(r"^\d{2}[-/]\d{2}[-/]\d{4}")

    i = data_start
    while i < len(lines):
        ln = lines[i].strip()
        if "total" in ln.lower():
            break

        if delimiter == "spaces" and date_re.match(ln):
            row_lines = [ln]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if date_re.match(nxt) or "total" in nxt.lower():
                    break
                row_lines.append(nxt)
                j += 1
            row_text = " ".join(row_lines)
            cells = _split_row(row_text, delimiter)
            i = j
        else:
            cells = _split_row(ln, delimiter)
            i += 1

        entry = {
            "invoice_number": None,
            "invoice_date": None,
            "customer_name": None,
            "customer_gstin": None,
            "place_of_supply": None,
            "reverse_charge": False,
            "invoice_type": "REGULAR",
            "taxable_value": 0.0,
            "igst": 0.0,
            "cgst": 0.0,
            "sgst": 0.0,
            "cess": 0.0,
            "total_value": 0.0,
            "hsn_summary": [],
            "raw_row": cells,
        }

        for idx, canon in mapping.items():
            if idx >= len(cells):
                continue
            val = cells[idx]
            if canon == "invoice_number":
                entry["invoice_number"] = val
            elif canon == "invoice_date":
                entry["invoice_date"] = _parse_date(val) or val
            elif canon == "customer_name":
                entry["customer_name"] = val
            elif canon == "customer_gstin":
                entry["customer_gstin"] = val
            elif canon == "place_of_supply":
                entry["place_of_supply"] = val
            elif canon == "reverse_charge":
                entry["reverse_charge"] = val.strip().lower() in {"y", "yes", "true"}
            elif canon == "invoice_type":
                entry["invoice_type"] = val or "REGULAR"
            elif canon == "taxable_value":
                entry["taxable_value"] = _parse_amount(val)
            elif canon == "igst":
                entry["igst"] = _parse_amount(val)
            elif canon == "cgst":
                entry["cgst"] = _parse_amount(val)
            elif canon == "sgst":
                entry["sgst"] = _parse_amount(val)
            elif canon == "cess":
                entry["cess"] = _parse_amount(val)
            elif canon == "total_value":
                entry["total_value"] = _parse_amount(val)

        if entry["total_value"] == 0 and entry["taxable_value"] > 0:
            entry["total_value"] = (
                entry["taxable_value"]
                + entry["igst"]
                + entry["cgst"]
                + entry["sgst"]
                + entry["cess"]
            )

        if not entry["invoice_number"] and entry["taxable_value"] == 0:
            warnings.append(f"row_skipped: {cells}")
            continue

        entries.append(entry)

    return {
        "doc_type": "sales_register",
        "gstin_of_business": None,
        "period": None,
        "entries": entries,
        "warnings": warnings,
        "meta": {
            "parser_version": "sales_register_v1",
            "source_format": delimiter,
        },
    }


def _main():
    if len(sys.argv) != 2:
        print("Usage: python sales_register.py <text_file_path>")
        raise SystemExit(1)
    path = Path(sys.argv[1])
    raw = path.read_text(encoding="utf-8")
    parsed = normalize_sales_register(raw)
    print(json.dumps(parsed, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _main()

