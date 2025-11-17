from __future__ import annotations

import re
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
NUM_PATTERN = re.compile(r"([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)")
SECTION_HEADER = re.compile(r"^[0-9]+\.")


def _collect_row_numbers(
    lines: List[str],
    start_idx: int,
    needed: int,
    max_lines: int = 10,
) -> List[str]:
    nums: List[str] = []
    for offset in range(max_lines):
        idx = start_idx + offset
        if idx >= len(lines):
            break
        line = lines[idx].strip()
        if offset > 0:
            if line.startswith("(") or line.endswith(":") or SECTION_HEADER.match(line):
                break
        found = NUM_PATTERN.findall(line)
        nums.extend(found)
        if len(nums) >= needed:
            break
    return nums


def _parse_amount(token: str) -> float:
    token = (token or "").strip().replace(",", "")
    if not token:
        return 0.0
    try:
        return float(token)
    except ValueError:
        return 0.0


def _find_first_match(pattern: re.Pattern, text: str) -> Optional[str]:
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _find_line_containing(lines: List[str], needle: str) -> Optional[int]:
    needle_lower = needle.lower()
    for i, line in enumerate(lines):
        if needle_lower in line.lower():
            return i
    return None


def normalize_gstr3b(raw_text: str) -> Dict[str, Any]:
    raw_lines = [ln.rstrip() for ln in raw_text.splitlines() if ln.strip()]
    merged_lines: List[str] = []
    num_only = re.compile(r"^[0-9,.\s]+$")
    for line in raw_lines:
        if num_only.match(line) and merged_lines:
            merged_lines[-1] = f"{merged_lines[-1]} {line.strip()}"
        else:
            merged_lines.append(line.strip())
    lines = merged_lines
    text = "\n".join(lines)
    warnings: List[str] = []

    # Header
    gstin = _find_first_match(re.compile(r"GSTIN:\s*([0-9A-Z]{15})"), text)
    legal_name = _find_first_match(re.compile(r"Legal Name:\s*(.+)"), text)
    trade_name = _find_first_match(re.compile(r"Trade Name:\s*(.+)"), text)

    period_month = None
    period_year = None
    m_period = re.search(r"For the Month of:\s*([A-Za-z]+)\s+([0-9]{4})", text)
    if m_period:
        month_name = m_period.group(1).lower()
        period_year = int(m_period.group(2))
        period_month = MONTHS.get(month_name)
    else:
        warnings.append("period_not_found")

    def _extract_supply_block(label: str) -> List[float]:
        idx = _find_line_containing(lines, label)
        if idx is None:
            warnings.append(f"{label}_not_found")
            return [0.0] * 5
        nums = _collect_row_numbers(lines, idx, 5)
        if len(nums) < 5:
            warnings.append(f"{label}_partial_parse")
            return [0.0] * 5
        return [_parse_amount(val) for val in nums[-5:]]

    outward_vals = _extract_supply_block("(a) Outward taxable supplies")
    rc_vals = _extract_supply_block("(d) Inward supplies liable to reverse charge")

    # ITC section
    def parse_itc_line(label_substring: str) -> Optional[List[float]]:
        idx = _find_line_containing(lines, label_substring)
        if idx is None:
            return None
        nums = _collect_row_numbers(lines, idx, 4)
        if len(nums) >= 4:
            return [_parse_amount(n) for n in nums[-4:]]
        return None

    def build_itc_block(label: str, warn_key: str) -> Dict[str, float]:
        vals = parse_itc_line(label)
        if vals:
            return {
                "igst": vals[0],
                "cgst": vals[1],
                "sgst": vals[2],
                "cess": vals[3],
            }
        warnings.append(warn_key)
        return {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}

    itc_from_imports = build_itc_block("ITC Available (import of goods/services)", "itc_imports_missing")
    itc_from_isd = build_itc_block("ITC from ISD", "itc_isd_missing")
    itc_on_inward = build_itc_block("ITC on inward supplies (other than RCM)", "itc_on_inward_missing")
    itc_on_inward_rcm = build_itc_block("ITC on inward supplies liable to RCM", "itc_rcm_missing")
    itc_total_vals = parse_itc_line("Total ITC Available")
    itc_total = {
        "igst": itc_total_vals[0] if itc_total_vals else 0.0,
        "cgst": itc_total_vals[1] if itc_total_vals else 0.0,
        "sgst": itc_total_vals[2] if itc_total_vals else 0.0,
        "cess": itc_total_vals[3] if itc_total_vals else 0.0,
    }

    # Exempt / Nil / Non-GST
    exempt = _parse_amount(
        _find_first_match(re.compile(r"^Exempt Supplies\s+([0-9.,]+)\s*$", re.MULTILINE), text) or "0"
    )
    nil_rated = _parse_amount(
        _find_first_match(re.compile(r"^Nil-Rated Supplies\s+([0-9.,]+)\s*$", re.MULTILINE), text) or "0"
    )
    non_gst = _parse_amount(
        _find_first_match(re.compile(r"^Non-GST Supplies\s+([0-9.,]+)\s*$", re.MULTILINE), text) or "0"
    )

    # Payment of tax
    def parse_tax_line(label: str) -> Dict[str, float]:
        idx = _find_line_containing(lines, label)
        if idx is None:
            warnings.append(f"{label.lower().replace(' ', '_')}_missing")
            return {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
        nums = _collect_row_numbers(lines, idx, 4)
        if len(nums) < 4:
            warnings.append(f"{label.lower().replace(' ', '_')}_partial")
            return {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
        vals = [_parse_amount(n) for n in nums[-4:]]
        return {"igst": vals[0], "cgst": vals[1], "sgst": vals[2], "cess": vals[3]}

    tax_payable = parse_tax_line("Tax Payable")
    tax_paid_itc = parse_tax_line("Tax Paid through ITC")
    tax_paid_cash = parse_tax_line("Tax Paid in Cash")

    # Verification
    ver_block_start = _find_line_containing(lines, "Verification")
    verification_text = "\n".join(lines[ver_block_start:]) if ver_block_start is not None else text
    ver_name = _find_first_match(re.compile(r"^Name:\s*(.+)$", re.MULTILINE), verification_text)
    ver_designation = _find_first_match(re.compile(r"^Designation:\s*(.+)$", re.MULTILINE), verification_text)
    ver_date_raw = _find_first_match(
        re.compile(r"^Date:\s*([0-9]{2}-[0-9]{2}-[0-9]{4})$", re.MULTILINE),
        verification_text,
    )
    ver_place = _find_first_match(re.compile(r"^Place:\s*(.+)$", re.MULTILINE), verification_text)

    ver_date_norm = None
    if ver_date_raw:
        day, month, year = ver_date_raw.split("-")
        ver_date_norm = f"{year}-{month}-{day}"

    period_label = None
    if period_month and period_year:
        month_name = list(MONTHS.keys())[period_month - 1].title()
        period_label = f"{month_name} {period_year}"

    result: Dict[str, Any] = {
        "doc_type": "gstr3b",
        "gstin": gstin,
        "legal_name": legal_name,
        "trade_name": trade_name,
        "period": {
            "month": period_month,
            "year": period_year,
            "label": period_label,
        },
        "outward_supplies": {
            "taxable_value": outward_vals[0],
            "igst": outward_vals[1],
            "cgst": outward_vals[2],
            "sgst": outward_vals[3],
            "cess": outward_vals[4],
        },
        "reverse_charge_inward_supplies": {
            "taxable_value": rc_vals[0],
            "igst": rc_vals[1],
            "cgst": rc_vals[2],
            "sgst": rc_vals[3],
            "cess": rc_vals[4],
        },
        "input_tax_credit": {
            "from_imports": itc_from_imports,
            "from_isd": itc_from_isd,
            "on_inward_supplies": itc_on_inward,
            "on_inward_supplies_reverse_charge": itc_on_inward_rcm,
            "total": itc_total,
        },
        "exempt_nil_nongst_supplies": {
            "exempt": exempt,
            "nil_rated": nil_rated,
            "non_gst": non_gst,
        },
        "tax_payable": tax_payable,
        "tax_paid": {
            "through_itc": tax_paid_itc,
            "in_cash": tax_paid_cash,
        },
        "verification": {
            "name": ver_name,
            "designation": ver_designation,
            "date": ver_date_norm,
            "place": ver_place,
        },
        "warnings": warnings,
        "meta": {
            "parser_version": "gstr3b_v1",
        },
    }

    if not gstin:
        warnings.append("gstin_missing")
    if not (period_month and period_year):
        warnings.append("period_incomplete")

    return result

