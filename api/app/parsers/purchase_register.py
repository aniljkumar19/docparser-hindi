from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import calendar

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

DATE_LINE_RE = re.compile(r"^\d{2}[-/]\d{2}[-/]\d{4}\b")
GSTIN_RE = re.compile(r"GSTIN:\s*([0-9A-Z]{15})", re.IGNORECASE)
PERIOD_RE = re.compile(r"purchase register\s*-\s*([A-Za-z]+)\s+(\d{4})", re.IGNORECASE)
AMOUNT_RE = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")
GSTIN_TOKEN_RE = re.compile(r"^[0-9]{2}[A-Z0-9]{10}[0-9A-Z]{3}$")


def _detect_delimiter(header_line: str) -> str:
    if "," in header_line:
        return ","
    if "\t" in header_line:
        return "\t"
    if ";" in header_line:
        return ";"
    return "spaces"


def _split_row(line: str, delimiter: str) -> List[str]:
    line = line.rstrip("\r\n")
    if delimiter == "spaces":
        parts = re.split(r"\s{2,}", line.strip())
    else:
        parts = [p.strip() for p in line.split(delimiter)]
    return [p for p in parts if p != ""]


def _normalize_header(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[\s._-]+", "", name)
    return name


def _parse_amount(value: str) -> float:
    value = value.strip().replace(",", "")
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _normalize_date(value: str) -> Optional[str]:
    value = value.strip()
    if not value:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", value)
    if m:
        return value
    m = re.match(r"(\d{2})[-/](\d{2})[-/](\d{4})", value)
    if m:
        d, mth, y = m.groups()
        return f"{y}-{mth}-{d}"
    return None


def _map_headers(header_cells: List[str]) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    for idx, raw in enumerate(header_cells):
        norm = _normalize_header(raw)
        if norm in {"date", "billdate", "invoicedate", "docdate"}:
            mapping[idx] = "invoice_date"
        elif norm in {"invoiceno", "invoicenumber", "billno", "billnumber", "docno", "refno"}:
            mapping[idx] = "invoice_number"
        elif norm in {"suppliername", "vendorname", "partyname"}:
            mapping[idx] = "supplier_name"
        elif norm in {"gstin", "supgstin", "suppliergstin", "vendorgstin"}:
            mapping[idx] = "supplier_gstin"
        elif norm in {"placeofsupply", "pos"}:
            mapping[idx] = "place_of_supply"
        elif norm in {"reversecharge", "rcm"}:
            mapping[idx] = "reverse_charge"
        elif norm in {"taxablevalue", "taxableamount", "taxable"}:
            mapping[idx] = "taxable_value"
        elif norm in {"igst", "igstamount"}:
            mapping[idx] = "igst"
        elif norm in {"cgst", "cgstamount"}:
            mapping[idx] = "cgst"
        elif norm in {"sgst", "sgstamount"}:
            mapping[idx] = "sgst"
        elif norm in {"cess", "cessamount"}:
            mapping[idx] = "cess"
        elif norm in {"total", "invoicevalue", "totalvalue", "grossamount"}:
            mapping[idx] = "total_value"
        elif norm in {"invoicetype", "doctype", "type"}:
            mapping[idx] = "invoice_type"
    return mapping


def _parse_fixed_width_row(line: str) -> Optional[Dict[str, Any]]:
    tokens = line.split()
    if len(tokens) < 8 or not DATE_LINE_RE.match(tokens[0]):
        return None

    invoice_number = tokens[1]
    gstin_idx: Optional[int] = None
    for idx in range(2, len(tokens)):
        if GSTIN_TOKEN_RE.match(tokens[idx]):
            gstin_idx = idx
            break
    if gstin_idx is None or gstin_idx - 2 < 1:
        return None

    supplier_name = " ".join(tokens[2:gstin_idx])
    supplier_gstin = tokens[gstin_idx]
    if gstin_idx + 1 >= len(tokens):
        return None
    place_of_supply = tokens[gstin_idx + 1]

    numeric_tokens = [t for t in tokens[gstin_idx + 2 :] if AMOUNT_RE.match(t)]
    if len(numeric_tokens) < 6:
        return None

    taxable_value = _parse_amount(numeric_tokens[0])
    igst = _parse_amount(numeric_tokens[1])
    cgst = _parse_amount(numeric_tokens[2])
    sgst = _parse_amount(numeric_tokens[3])
    cess = _parse_amount(numeric_tokens[4])
    total_value = _parse_amount(numeric_tokens[5])

    return {
        "invoice_number": invoice_number,
        "invoice_date": _normalize_date(tokens[0]) or tokens[0],
        "supplier_name": supplier_name,
        "supplier_gstin": supplier_gstin,
        "place_of_supply": place_of_supply,
        "reverse_charge": False,
        "invoice_type": "REGULAR",
        "taxable_value": taxable_value,
        "igst": igst,
        "cgst": cgst,
        "sgst": sgst,
        "cess": cess,
        "total_value": total_value,
        "hsn_summary": [],
        "raw_row": {"tokens": tokens},
    }


def purchase_register_total_taxable(purchase_register: Dict[str, Any]) -> float:
    total = 0.0
    for entry in purchase_register.get("entries") or []:
        try:
            total += float(entry.get("taxable_value") or 0.0)
        except (TypeError, ValueError):
            continue
    return round(total, 2)


def normalize_purchase_register(raw_text: str) -> Dict[str, Any]:
    raw_lines = raw_text.splitlines()
    lines = [ln for ln in raw_lines if ln.strip()]
    warnings: List[str] = []
    gstin_of_business = None
    period = None

    gstin_match = GSTIN_RE.search(raw_text)
    if gstin_match:
        gstin_of_business = gstin_match.group(1)

    period_match = PERIOD_RE.search(raw_text)
    if period_match:
        month_name = period_match.group(1).lower()
        year = int(period_match.group(2))
        month = MONTHS.get(month_name)
        if month:
            days = calendar.monthrange(year, month)[1]
            start = f"{year}-{month:02d}-01"
            end = f"{year}-{month:02d}-{days:02d}"
            period = {
                "start": start,
                "end": end,
                "label": f"{month_name.title()} {year}",
            }

    if not lines:
        return {
            "doc_type": "purchase_register",
            "gstin_of_business": gstin_of_business,
            "period": period,
            "entries": [],
            "warnings": ["empty_input"],
            "meta": {"parser_version": "purchase_register_v1", "source_format": None},
        }

    header_idx = None
    header_line = lines[0]
    skip_indices = set()
    for idx, line in enumerate(lines):
        low = line.lower()
        if "invoice date" in low and "supplier" in low:
            header_idx = idx
            header_line = line
            skip_indices.add(idx)
            if idx + 1 < len(lines):
                next_line = lines[idx + 1].strip()
                if any(
                    token in next_line.lower()
                    for token in ("igst", "cgst", "sgst", "invoice value", "taxable value")
                ):
                    header_line = f"{header_line.strip()} {next_line.strip()}"
                    skip_indices.add(idx + 1)
            break

    data_start_idx = 0
    if header_idx is not None:
        data_start_idx = max(skip_indices) + 1 if skip_indices else header_idx + 1
    else:
        header_idx = 0
        header_line = lines[0]
        data_start_idx = 1

    delimiter = _detect_delimiter(header_line)
    header_cells = _split_row(header_line, delimiter)
    col_mapping = _map_headers(header_cells)
    if not col_mapping:
        warnings.append("no_known_columns_found")

    entries: List[Dict[str, Any]] = []
    data_lines = lines[data_start_idx:]
    i = 0
    while i < len(data_lines):
        row_line = data_lines[i].strip()
        if not row_line:
            i += 1
            continue
        if row_line.startswith("----") or row_line.lower().startswith("total invoices"):
            i += 1
            continue

        if delimiter == "spaces" and DATE_LINE_RE.match(row_line):
            row_lines = [row_line]
            j = i + 1
            while j < len(data_lines):
                nxt = data_lines[j].strip()
                if not nxt:
                    j += 1
                    continue
                if DATE_LINE_RE.match(nxt) or nxt.startswith("----") or nxt.lower().startswith("total"):
                    break
                row_lines.append(nxt)
                j += 1
            row_line = " ".join(row_lines)
            i = j
        else:
            i += 1

        if delimiter == "spaces":
            fixed_row = _parse_fixed_width_row(row_line)
            if fixed_row:
                entries.append(fixed_row)
                continue

        cells = _split_row(row_line, delimiter)
        if not cells:
            continue

        row_raw: Dict[str, Any] = {}
        row_norm: Dict[str, Any] = {
            "invoice_number": None,
            "invoice_date": None,
            "supplier_name": None,
            "supplier_gstin": None,
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
            "raw_row": row_raw,
        }

        for idx, cell in enumerate(cells):
            key = header_cells[idx] if idx < len(header_cells) else f"col_{idx}"
            row_raw[key] = cell

        for idx, canon in col_mapping.items():
            if idx >= len(cells):
                continue
            val = cells[idx]
            if canon == "invoice_number":
                row_norm["invoice_number"] = val
            elif canon == "invoice_date":
                row_norm["invoice_date"] = _normalize_date(val) or val
            elif canon == "supplier_name":
                row_norm["supplier_name"] = val
            elif canon == "supplier_gstin":
                row_norm["supplier_gstin"] = val
            elif canon == "place_of_supply":
                row_norm["place_of_supply"] = val
            elif canon == "reverse_charge":
                row_norm["reverse_charge"] = val.strip().upper().startswith(("Y", "T"))
            elif canon == "invoice_type":
                row_norm["invoice_type"] = val or "REGULAR"
            elif canon == "taxable_value":
                row_norm["taxable_value"] = _parse_amount(val)
            elif canon == "igst":
                row_norm["igst"] = _parse_amount(val)
            elif canon == "cgst":
                row_norm["cgst"] = _parse_amount(val)
            elif canon == "sgst":
                row_norm["sgst"] = _parse_amount(val)
            elif canon == "cess":
                row_norm["cess"] = _parse_amount(val)
            elif canon == "total_value":
                row_norm["total_value"] = _parse_amount(val)

        if row_norm["total_value"] == 0.0 and row_norm["taxable_value"] > 0:
            taxes = (
                row_norm["igst"]
                + row_norm["cgst"]
                + row_norm["sgst"]
                + row_norm["cess"]
            )
            row_norm["total_value"] = row_norm["taxable_value"] + taxes

        if not row_norm["invoice_number"] and row_norm["taxable_value"] == 0.0:
            warnings.append(
                f"row_skipped_no_invoice_number_and_zero_taxable: {row_raw}"
            )
            continue

        entries.append(row_norm)

    return {
        "doc_type": "purchase_register",
        "gstin_of_business": gstin_of_business,
        "period": period,
        "entries": entries,
        "warnings": warnings,
        "meta": {
            "parser_version": "purchase_register_v1",
            "source_format": "spaces" if delimiter == "spaces" else "delimited",
        },
    }


def _main():
    if len(sys.argv) != 2:
        print("Usage: python purchase_register.py <text_file_path>")
        raise SystemExit(1)

    path = Path(sys.argv[1])
    raw = path.read_text(encoding="utf-8")
    parsed = normalize_purchase_register(raw)
    print(json.dumps(parsed, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _main()

