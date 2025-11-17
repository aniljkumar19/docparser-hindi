# api/app/parsers/bank_normalizer.py
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .policy_loader import ParserPolicy
from .tx_rules import RESIDUAL_RULES, RULES_MAP

_MON = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
MONTH_TOKEN = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"


def _clean_ocr_numbers(value: str) -> str:
    value = value.replace("§", "5").replace("S", "5")
    value = value.replace("O", "0").replace("o", "0")
    value = value.replace("l", "1").replace("I", "1")
    value = value.replace("—", "-").replace("–", "-")
    value = re.sub(r"[ 	]+", " ", value)
    return value.strip()


def _money(token: str) -> float:
    token = token.strip()
    if token in ("", "-", "—"):
        return 0.0
    token = token.replace("$", "").replace(",", "")
    token = re.sub(r"[^\d.\-]", "", token)
    return float(token) if token else 0.0


def _norm_date_mmdd(
    token: str,
    year: int,
    allowed_months: Optional[Set[int]] = None,
    fallback_month: Optional[int] = None,
) -> Optional[str]:
    token = token.strip("-/ ")
    if not token:
        return None
    match = re.match(r"^(\d{1,2})[-/](\d{1,2})(?:[-/](\d{2,4}))?$", token)
    if not match:
        match = re.search(r"(\d{1,2})[-/](\d{1,2})", token)
        if not match:
            return None
    first, second = int(match.group(1)), int(match.group(2))
    year_token = match.group(3)

    if year_token:
        year_val = int(year_token)
        if year_val < 100:
            year_val = 2000 + year_val
    else:
        year_val = year

    month: Optional[int] = None
    day: Optional[int] = None

    candidates: List[Tuple[int, int]] = []
    if 1 <= first <= 12:
        candidates.append((first, second))
    if 1 <= second <= 12:
        candidates.append((second, first))

    if allowed_months:
        for candidate_month, candidate_day in candidates:
            if candidate_month in allowed_months:
                month, day = candidate_month, candidate_day
                break

    if month is None and fallback_month and 1 <= fallback_month <= 12 and 1 <= first <= 31:
        month = fallback_month
        day = first

    if month is None and candidates:
        month, day = candidates[0]

    if month is None:
        month = min(max(first, 1), 12)
        day = second
    if day is None:
        day = second if month == first else first

    try:
        return datetime(year_val, month, day).date().isoformat()
    except ValueError:
        return None


def _infer_period_and_year(text: str, fallback_year: Optional[int] = None) -> Tuple[Optional[str], Optional[str], int]:
    content = (text or "").lower()
    pairs: List[Tuple[int, int]] = []

    for match in re.finditer(rf"\b{MONTH_TOKEN}\s+(\d{{1,2}})\b", content, re.I):
        mon = match.group(1)[:4].lower()
        day = int(match.group(2))
        if mon in _MON:
            pairs.append((_MON[mon], day))

    if not pairs:
        year = fallback_year or datetime.utcnow().year
        return None, None, year

    pairs.sort()
    start_m, start_d = pairs[0]
    end_m, end_d = pairs[-1]
    current_year = fallback_year or datetime.utcnow().year

    if start_m > end_m:
        start_year = current_year - 1
        end_year = current_year
    else:
        start_year = end_year = current_year

    start = f"{start_year:04d}-{start_m:02d}-{start_d:02d}"
    end = f"{end_year:04d}-{end_m:02d}-{end_d:02d}"
    return start, end, end_year


def _clean_description(desc: str) -> str:
    desc = desc.strip()
    if not desc:
        return desc
    replacements = [
        (r"(?i)preauthorizedcredit", "PREAUTHORIZED CREDIT"),
        (r"(?i)preauthorized\s*cred[i1]t", "PREAUTHORIZED CREDIT"),
        (r"(?i)p\s*0\s*s", "POS"),
        (r"(?i)p0s", "POS"),
        (r"(?i)po5", "POS"),
        (r"(?i)pos\s*purcha[s5]e", "POS PURCHASE"),
        (r"(?i)atm\s*w[1l]th", "ATM WITH"),
        (r"(?i)auth0rized", "AUTHORIZED"),
        (r"(?i)in[t1]erest\s*cred[i1]t", "INTEREST CREDIT"),
        (r"(?i)5ervice", "SERVICE"),
        (r"(?i)w1th", "WITH"),
        (r"(?i)c0urt", "COURT"),
        (r"(?i)depos1t", "DEPOSIT"),
        (r"(?i)1nterest", "INTEREST"),
        (r"(?i)atm w1thdrawal", "ATM WITHDRAWAL"),
    ]
    for pattern, replacement in replacements:
        desc = re.sub(pattern, replacement, desc)
    if re.search(r"(?i)^[\dO]+$", desc):
        return desc
    desc = re.sub(r"(?<=CHECK)\s+([\d]+)[A-Z]?$", lambda m: f" {m.group(1)}", desc)
    desc = re.sub(r"\s+", " ", desc)
    return desc.strip()


def _finalize_description(desc: str) -> str:
    if not desc:
        return ""
    return desc.replace("§", "5").replace("—", "-").strip()


@dataclass
class Transaction:
    date: Optional[str]
    description: str
    debit: float = 0.0
    credit: float = 0.0
    balance: Optional[float] = None
    channel: Optional[str] = None
    _residual: Optional[float] = field(default=None, repr=False)


def _normalize_descriptions(txns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for txn in txns:
        desc = _clean_description(str(txn.get("description", "")))
        cleaned.append({**txn, "description": desc})
    return cleaned


@dataclass
class NormalizeResult:
    period_start: Optional[str]
    period_end: Optional[str]
    year: int
    opening_balance: Optional[float]
    closing_balance: Optional[float]
    transactions: List[Dict[str, Any]]
    totals: Dict[str, Any]
    warnings: List[str]
    profile_name: str
    reconciliation_rate: float
    closing_drift: float


def _apply_rule(rule_name: str, txn: Transaction, residual: Optional[float] = None) -> bool:
    fn = RULES_MAP.get(rule_name)
    if not fn:
        return False
    try:
        return bool(fn(txn, residual))
    except Exception:
        return False


def normalize_bank_statement(
    *,
    ocr_text: str,
    transactions: List[Dict[str, Any]],
    opening_balance: Optional[float],
    closing_balance: Optional[float],
    fallback_year: Optional[int] = None,
    profile: Optional[ParserPolicy] = None,
) -> NormalizeResult:
    period_start, period_end, year = _infer_period_and_year(ocr_text, fallback_year)
    period_months: Optional[Set[int]] = None
    if period_start and period_end:
        try:
            ps = datetime.fromisoformat(period_start)
            pe = datetime.fromisoformat(period_end)
            period_months = {ps.month, pe.month}
        except Exception:
            period_months = None

    normalizable = _normalize_descriptions(transactions or [])

    normalized: List[Transaction] = []
    for txn in normalizable:
        debit = txn.get("debit")
        credit = txn.get("credit")
        balance = txn.get("balance")

        debit_val = _money(_clean_ocr_numbers(str(debit))) if debit is not None else 0.0
        credit_val = _money(_clean_ocr_numbers(str(credit))) if credit is not None else 0.0
        balance_val = _money(_clean_ocr_numbers(str(balance))) if balance is not None else None

        raw_date = str(txn.get("date") or "")
        norm_date = None
        if raw_date:
            cleaned_date = raw_date.replace("--", "").replace(" ", "")
            fallback_month = None
            digits = re.findall(r"\d{1,2}", cleaned_date)
            if period_months:
                fallback_month = sorted(period_months)[0]
            elif digits:
                try:
                    fallback_month = int(digits[1]) if len(digits) > 1 and int(digits[1]) <= 12 else int(digits[0])
                except Exception:
                    fallback_month = None
            norm_date = _norm_date_mmdd(cleaned_date, year, allowed_months=period_months, fallback_month=fallback_month)
            if norm_date is None:
                norm_date = _norm_date_mmdd(cleaned_date, year)

        normalized.append(
            Transaction(
                date=norm_date,
                description=txn.get("description", ""),
                debit=debit_val,
                credit=credit_val,
                balance=balance_val,
                channel=txn.get("channel"),
            )
        )

    warnings: List[str] = []
    profile_obj = profile or ParserPolicy(name="generic", residual_tolerance=1.0, tx_rules=[])
    rule_names = [name for name in (profile_obj.tx_rules or []) if name in RULES_MAP]
    pre_rules = [name for name in rule_names if name not in RESIDUAL_RULES]
    residual_rules = [name for name in rule_names if name in RESIDUAL_RULES]

    for tr in normalized:
        for rule_name in pre_rules:
            _apply_rule(rule_name, tr)

    reconciliation_rate = 1.0
    closing_drift = 0.0
    matched = 0
    within_tolerance = 0

    if opening_balance is not None:
        previous = round(float(opening_balance), 2)
        for tr in normalized:
            expected = round(previous + tr.credit - tr.debit, 2)
            if tr.balance is not None:
                residual = round(tr.balance - expected, 2)
                for rule_name in residual_rules:
                    if _apply_rule(rule_name, tr, residual):
                        expected = round(previous + tr.credit - tr.debit, 2)
                        residual = round(tr.balance - expected, 2)
                tr._residual = residual
                previous = tr.balance
                matched += 1
                if abs(residual) <= profile_obj.residual_tolerance:
                    within_tolerance += 1
            else:
                previous = expected

        if matched:
            reconciliation_rate = within_tolerance / matched

        computed = round(float(opening_balance) + sum(t.credit - t.debit for t in normalized), 2)
        if closing_balance is not None:
            closing_drift = round(float(closing_balance) - computed, 2)
            if abs(closing_drift) > profile_obj.residual_tolerance:
                warnings.append(f"Balance drift detected (≈{abs(closing_drift):.2f})")

    total_debits = round(sum(t.debit for t in normalized), 2)
    total_credits = round(sum(t.credit for t in normalized), 2)
    totals = {
        "debits": total_debits,
        "credits": total_credits,
        "count": len(normalized),
        "closing_balance": closing_balance,
    }

    out_txns: List[Dict[str, Any]] = []
    for tr in normalized:
        row: Dict[str, Any] = {
            "date": tr.date,
            "description": _finalize_description(tr.description),
            "debit": round(tr.debit, 2),
            "credit": round(tr.credit, 2),
        }
        if tr.balance is not None:
            row["balance"] = round(tr.balance, 2)
        channel = tr.channel
        if channel:
            row["channel"] = channel
        if row["description"].upper().startswith("CHECK") and "channel" not in row:
            row["channel"] = "CHECK"
        if tr._residual is not None and abs(tr._residual) > 1.0:
            row["_residual"] = round(tr._residual, 2)
        out_txns.append(row)

    deduped: List[str] = []
    seen = set()
    for item in warnings:
        if item not in seen:
            deduped.append(item)
            seen.add(item)

    return NormalizeResult(
        period_start=period_start,
        period_end=period_end,
        year=year,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        transactions=out_txns,
        totals=totals,
        warnings=deduped,
        profile_name=profile_obj.name,
        reconciliation_rate=round(reconciliation_rate, 3),
        closing_drift=round(closing_drift, 2),
    )
