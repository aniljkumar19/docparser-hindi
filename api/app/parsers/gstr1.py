from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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

GSTIN_LINE_RE = re.compile(r"^[0-9]{2}[A-Z0-9]{10}[0-9A-Z]{3}")
DATE_TOKEN_RE = re.compile(r"\d{2}-\d{2}-\d{4}")
POS_TOKEN_RE = re.compile(r"\d{2}-[A-Za-z]")
NUMERIC_TOKEN_RE = re.compile(r"^[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?$")


def _parse_amount(s: str) -> float:
    s = s.strip().replace(",", "")
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _find_first(pattern: str, text: str, flags: int = 0) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _normalize_date_ddmmyyyy(s: str) -> Optional[str]:
    """
    Convert DD-MM-YYYY or DD/MM/YYYY -> YYYY-MM-DD
    """

    s = s.strip()
    m = re.match(r"(\d{2})[-/](\d{2})[-/](\d{4})", s)
    if not m:
        return None
    d, mth, y = m.groups()
    return f"{y}-{mth}-{d}"


def _split_row(line: str) -> List[str]:
    """
    Split a table row into columns. We start with a generic '2+ spaces' split.
    If your export uses | separators, change this to line.split('|').
    """

    parts = re.split(r"\s{2,}", line.strip())
    return [p for p in parts if p]


def normalize_gstr1(raw_text: str) -> Dict[str, Any]:
    """
    Normalize a GSTR-1 text extract into structured JSON.

    v1: header + B2B invoices.
    """

    lines = [ln.rstrip("\r\n") for ln in raw_text.splitlines()]
    lines = [ln for ln in lines if ln.strip()]
    text = "\n".join(lines)
    warnings: List[str] = []

    gstin = _find_first(r"GSTIN:\s*([0-9A-Z]{15})", text)
    legal_name = _find_first(r"Legal Name:\s*(.+)", text)
    trade_name = _find_first(r"Trade Name:\s*(.+)", text)

    month: Optional[int] = None
    year: Optional[int] = None
    m = re.search(r"For the Month of:\s*([A-Za-z]+)\s+([0-9]{4})", text)
    if m:
        month_name = m.group(1).lower()
        year = int(m.group(2))
        month = MONTHS.get(month_name)
    else:
        warnings.append("period_not_found")

    b2b_invoices: List[Dict[str, Any]] = []
    b2b_start_idx: Optional[int] = None
    for i, ln in enumerate(lines):
        if "B2B" in ln and ("4A" in ln or "4A." in ln or "B2B Invoices" in ln):
            b2b_start_idx = i
            break

    def _process_row(buffer: List[str]):
        nonlocal b2b_invoices, warnings
        if not buffer:
            return
        row_text = "  ".join(buffer)
        trimmed = row_text.replace("-", "").strip()
        if not trimmed:
            return
        if "CGST" in row_text and "Cess" in row_text:
            return

        try:
            line1 = buffer[0] if buffer else ""
            parts1 = re.split(r"\s{2,}", line1.strip())
            if len(parts1) < 4:
                warnings.append(f"b2b_row_skipped_insufficient_columns: {row_text}")
                return
            gstin_token = parts1[0].split()[0]
            invoice_number = parts1[2] if len(parts1) > 2 else None
            date_token = None
            invoice_value_token = None
            tail = parts1[3:]
            if tail:
                if len(tail) >= 2:
                    date_token = tail[0]
                    invoice_value_token = tail[1]
                else:
                    match = DATE_TOKEN.search(tail[0])
                    if match:
                        date_token = match.group(1)
                        remainder = tail[0][match.end():].strip()
                        invoice_value_token = remainder or None
            invoice_date = _normalize_date_ddmmyyyy(date_token or "") or date_token
            _ = _parse_amount(invoice_value_token or "0")

            line2 = buffer[1] if len(buffer) > 1 else ""
            parts2 = re.split(r"\s{2,}", line2.strip()) if line2 else []
            place_of_supply = parts2[0] if parts2 else None
            reverse_token = (parts2[1] if len(parts2) > 1 else "").strip().upper()
            reverse_charge_flag = reverse_token.startswith(("Y", "YES"))
            invoice_type = parts2[2] if len(parts2) > 2 else "REGULAR"
            taxable_value = _parse_amount(parts2[4]) if len(parts2) > 4 else 0.0
            igst = _parse_amount(parts2[5]) if len(parts2) > 5 else 0.0

            line3 = buffer[2] if len(buffer) > 2 else ""
            number_tokens = re.findall(AMOUNT_TOKEN, line3)
            while len(number_tokens) < 3:
                number_tokens.append("0.0")
            cgst = _parse_amount(number_tokens[0])
            sgst = _parse_amount(number_tokens[1])
            cess = _parse_amount(number_tokens[2])

            b2b_invoices.append(
                {
                    "invoice_number": invoice_number,
                    "invoice_date": invoice_date,
                    "counterparty_gstin": gstin_token,
                    "place_of_supply": place_of_supply,
                    "reverse_charge": reverse_charge_flag,
                    "invoice_type": invoice_type or "REGULAR",
                    "taxable_value": taxable_value,
                    "igst": igst,
                    "cgst": cgst,
                    "sgst": sgst,
                    "cess": cess,
                }
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"b2b_row_parse_error: {row_text} ({exc})")

    if b2b_start_idx is not None:
        header_idx: Optional[int] = None
        for j in range(b2b_start_idx, min(b2b_start_idx + 10, len(lines))):
            if "GSTIN" in lines[j] and "Invoice Number" in lines[j]:
                header_idx = j
                break

        data_start = (header_idx + 1) if header_idx is not None else (b2b_start_idx + 1)

        i = data_start
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            if (
                line.startswith("5.")
                or "B2C" in line
                or "HSN-wise" in line
                or line.startswith("-----")
            ):
                break

            if GSTIN_LINE_RE.match(line):
                row_lines = [line]
                j = i + 1
                while j < len(lines):
                    nxt = lines[j].strip()
                    if not nxt:
                        j += 1
                        continue
                    if GSTIN_LINE_RE.match(nxt):
                        break
                    if (
                        nxt.startswith("5.")
                        or "B2C" in nxt
                        or "HSN-wise" in nxt
                        or nxt.startswith("-----")
                    ):
                        break
                    row_lines.append(nxt)
                    j += 1

                row_text = " ".join(row_lines)
                tokens = row_text.split()

                try:
                    counterparty_gstin = tokens[0]
                    invoice_number = next(
                        (t for t in tokens if t.upper().startswith("INV-")), None
                    )
                    date_token = next(
                        (t for t in tokens if DATE_TOKEN_RE.match(t)), None
                    )
                    invoice_date = (
                        _normalize_date_ddmmyyyy(date_token) if date_token else None
                    )
                    pos_token = next(
                        (t for t in tokens if POS_TOKEN_RE.match(t)), None
                    )
                    rc_token = next(
                        (t for t in tokens if t.upper() in {"Y", "N"}), "N"
                    )
                    invoice_type = next(
                        (
                            t
                            for t in tokens
                            if t.upper()
                            in {"REGULAR", "SEZ", "DEEMED", "EXP", "EXPORT"}
                        ),
                        "REGULAR",
                    )

                    num_tokens = [t for t in tokens if NUMERIC_TOKEN_RE.match(t)]
                    if len(num_tokens) >= 6:
                        taxable_value = _parse_amount(num_tokens[-5])
                        igst = _parse_amount(num_tokens[-4])
                        cgst = _parse_amount(num_tokens[-3])
                        sgst = _parse_amount(num_tokens[-2])
                        cess = _parse_amount(num_tokens[-1])
                    else:
                        taxable_value = igst = cgst = sgst = cess = 0.0
                        warnings.append(f"b2b_numeric_partial_parse: {row_text}")

                    b2b_invoices.append(
                        {
                            "invoice_number": invoice_number,
                            "invoice_date": invoice_date,
                            "counterparty_gstin": counterparty_gstin,
                            "place_of_supply": pos_token,
                            "reverse_charge": rc_token.upper() == "Y",
                            "invoice_type": invoice_type,
                            "taxable_value": taxable_value,
                            "igst": igst,
                            "cgst": cgst,
                            "sgst": sgst,
                            "cess": cess,
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"b2b_row_parse_error: {row_text} ({exc})")

                i = j
            else:
                i += 1

        if not b2b_invoices:
            warnings.append("b2b_invoices_not_parsed")
    else:
        warnings.append("b2b_section_not_found")

    result: Dict[str, Any] = {
        "doc_type": "gstr1",
        "gstin": gstin,
        "legal_name": legal_name,
        "trade_name": trade_name,
        "period": {
            "month": month,
            "year": year,
            "label": f"{list(MONTHS.keys())[month - 1].title()} {year}"
            if month and year
            else None,
        },
        "b2b_invoices": b2b_invoices,
        "b2c_large": [],
        "credit_debit_notes": [],
        "hsn_summary": [],
        "warnings": warnings,
        "meta": {
            "parser_version": "gstr1_v1",
        },
    }

    if not gstin:
        warnings.append("gstin_missing")
    if not (month and year):
        warnings.append("period_incomplete")

    return result


def gstr1_outward_totals(parsed: Dict[str, Any]) -> float:
    total = 0.0
    for inv in parsed.get("b2b_invoices") or []:
        try:
            total += float(inv.get("taxable_value") or 0.0)
        except (TypeError, ValueError):
            continue
    return round(total, 2)


def _main():
    if len(sys.argv) != 2:
        print("Usage: python gstr1.py <text_file_path>")
        raise SystemExit(1)

    path = Path(sys.argv[1])
    raw = path.read_text(encoding="utf-8")
    parsed = normalize_gstr1(raw)
    print(json.dumps(parsed, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _main()

