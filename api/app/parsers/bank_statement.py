# api/app/parsers/bank_statement.py
import re
from datetime import datetime
from typing import Optional

AMT = r"-?[₹$]?\s*\d[\d,]*(?:\.\d{1,2})?"
DATE = r"(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{4}[/-]\d{1,2}[/-]\d{1,2})"

TXN_LINE = re.compile(
    rf"^\s*(?P<date>{DATE})(?:[.,])?\s+"
    r"(?P<narr>.+?)\s+"
    rf"(?:(?P<debit>{AMT})\s+)?"
    rf"(?:(?P<credit>{AMT})\s+)?"
    rf"(?P<bal>{AMT})?\s*$",
    re.I
)

TXN_LINE_ALT = re.compile(
    rf"^\s*(?P<date>{DATE})(?:[.,])?\s+"
    r"(?P<narr>.+?)\s+"
    rf"(?P<amt>{AMT})\s+(?P<type>dr|cr)\s+"
    rf"(?P<bal>{AMT})?\s*$",
    re.I
)

DEBIT_MARK = re.compile(r"(?i)\b(debit|dr|withdrawal|atm|pos|upi\s*pay|ach\s*debit)\b")
CREDIT_MARK = re.compile(r"(?i)\b(credit|cr|deposit|neft|rtgs|imps|upi\s*in|income)\b")

CHANNEL_CUES = {
    "UPI": ("upi", "bharatpe", "phonepe", "paytm"),
    "NEFT": ("neft",),
    "IMPS": ("imps",),
    "RTGS": ("rtgs",),
    "CHEQUE": ("cheque", "chq"),
    "ATM": ("atm",),
    "POS": ("pos",)
}

ACC_REGEX = re.compile(r"(?i)\b(acc(?:ount)?(?:\s*(?:no|number|#|:))?\s*[:\-]?\s*)([A-Z0-9\-\*Xx]{6,})")
IFSC_REGEX = re.compile(r"(?i)\bIFSC\b[:\s-]*([A-Z]{4}0[A-Z0-9]{6})")
PERIOD_REGEX = re.compile(r"(?is)statement\s+period.*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")
ALT_PERIOD_REGEX = re.compile(r"(?i)(?:period|from)\s*(?:to|-)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")
OPEN_BAL_REGEX = re.compile(r"(?i)\b(opening|balance\s*b\/f)\b.*?(" + AMT + r")")
BEGIN_BAL_REGEX = re.compile(r"(?is)\b(beginning|starting)\s+balance.*?(" + AMT + r")")
CLOSE_BAL_REGEX = re.compile(r"(?is)(closing|ending|balance\s*c\/f).*?(" + AMT + r")")

TXN_LINE_AMT_BAL = re.compile(
    rf"^\s*(?P<date>{DATE})(?:[.,])?\s+(?P<narr>.+?)\s+(?P<amount>{AMT})\s+(?P<bal>{AMT})\s*$",
    re.I
)


def _clean_amount_token(s: str) -> str:
    token = (s or "").strip()
    token = token.replace("₹", "").replace("$", "").replace(",", "")
    token = token.replace("—", "-").replace("–", "-")
    token = token.replace("O", "0").replace("o", "0").replace("I", "1").replace("l", "1")
    token = re.sub(r"(?i)(cr|dr)$", "", token)
    return token


def _parse_amount(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    token = _clean_amount_token(s)
    if token in {"", "-", "--"}:
        return 0.0
    digits_only = token.replace("-", "").replace(".", "")
    if len(digits_only) > 12 and "." not in token:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def _norm_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip().replace("O", "0")
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$", s)
    if m:
        d, mo, y2 = map(int, m.groups())
        y = 2000 + y2
        try:
            return datetime(y, mo, d).date().isoformat()
        except Exception:
            pass
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})$", s)
    if m:
        d, mo = map(int, m.groups())
        return f"--{mo:02d}-{d:02d}"
    return s


def _detect_channel(desc: str) -> Optional[str]:
    low = desc.lower()
    for name, cues in CHANNEL_CUES.items():
        if any(c in low for c in cues):
            return name
    return None


def _amount_from_line(line: str, prefer_last: bool = False) -> Optional[float]:
    matches = []
    for m in re.finditer(r"(?:[₹$]\s*)?(\d[\d,]*(?:\.\d{1,2})?)", line):
        token = m.group(1)
        prefix = m.group(0).strip()
        has_currency = prefix.startswith("₹") or prefix.startswith("$")
        has_decimal = "." in token
        matches.append((token, has_currency, has_decimal))
    iterable = reversed(matches) if prefer_last else matches
    for token, has_currency, has_decimal in iterable:
        if has_currency or has_decimal:
            return _parse_amount(token)
    if matches:
        token = matches[-1][0] if prefer_last else matches[0][0]
        return _parse_amount(token)
    return None


def parse_text_rules(text: str, confidence: float | None = None) -> dict:
    cleaned = text.replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]

    result = {
        "bank": {},
        "account": {},
        "statement": {
            "period": {"from": None, "to": None},
            "account": {"masked": None, "last4": None, "ifsc": None},
        },
        "period": {"start": None, "end": None},
        "opening_balance": None,
        "closing_balance": None,
        "currency": "INR" if "₹" in text else ("USD" if "$" in text else None),
        "transactions": [],
        "totals": {"debits": 0.0, "credits": 0.0, "count": 0, "closing_balance": None},
        "warnings": [],
    }

    full_text = "\n".join(lines)

    # bank name
    for line in lines:
        if "bank" in line.lower():
            result["bank"]["name"] = line
            break
    if "name" not in result["bank"] and lines:
        result["bank"]["name"] = lines[0]

    # account info
    acc_match = ACC_REGEX.search(full_text)
    if acc_match:
        masked = acc_match.group(2)
        result["account"]["number"] = masked
        digits = re.sub(r"[^0-9]", "", masked)
        if len(digits) >= 4:
            result["account"]["last4"] = digits[-4:]
            result["statement"]["account"]["last4"] = digits[-4:]
        result["statement"]["account"]["masked"] = masked

    ifsc_match = IFSC_REGEX.search(full_text)
    if ifsc_match:
        result["statement"]["account"]["ifsc"] = ifsc_match.group(1).upper()

    # statement period
    period_match = PERIOD_REGEX.search(full_text) or ALT_PERIOD_REGEX.search(full_text)
    if period_match:
        start = _norm_date(period_match.group(1))
        end = _norm_date(period_match.group(2))
        result["period"]["start"] = start
        result["period"]["end"] = end
        result["statement"]["period"] = {"from": start, "to": end}

    # balances
    for line in lines[:20]:
        low = line.lower()
        if any(token in low for token in ("beginning balance", "opening balance")) and result.get("opening_balance") is None:
            amount = _amount_from_line(line)
            if amount is not None:
                result["opening_balance"] = amount
        if any(token in low for token in ("ending balance", "closing balance", "balance c/f")) and result.get("closing_balance") is None:
            amount = _amount_from_line(line)
            if amount is None:
                amount = _amount_from_line(line, prefer_last=True)
            if amount is not None:
                result["closing_balance"] = amount

    txn_break_markers = ("account transactions by type", "deposits and other credits", "withdrawals and other debits")
    txn_pattern = re.compile(rf"^\s*(?P<date>{DATE})(?:[.,])?\s+(?P<rest>.+)$", re.I)

    prev_balance = result.get("opening_balance")
    started_txns = False
    for line in lines:
        low = line.lower()
        if any(marker in low for marker in txn_break_markers):
            if started_txns:
                break
            else:
                continue
        if re.search(r"date\s+(narration|description).*balance", low):
            started_txns = True
            continue

        m = txn_pattern.match(line)
        if not m:
            continue
        started_txns = True
        date_raw = (m.group("date") or "").rstrip(".,")
        rest = m.group("rest")

        numeric_matches = list(re.finditer(r"(?:[₹$]\s*)?(\d[\d,]*(?:\.\d{1,2})?)", rest))
        if not numeric_matches:
            continue

        balance_match = numeric_matches[-1]
        balance = _parse_amount(balance_match.group(1))

        amount_match = None
        for candidate in reversed(numeric_matches[:-1]):
            token = candidate.group(1)
            prefix = candidate.group(0).strip()
            if prefix.startswith("₹") or prefix.startswith("$") or "." in token:
                amount_match = candidate
                break
        if amount_match is None and len(numeric_matches) >= 2:
            amount_match = numeric_matches[-2]
        if amount_match is None:
            continue

        amount_val = _parse_amount(amount_match.group(1))
        if amount_val is None:
            continue

        desc_end = amount_match.start()
        description = (rest[:desc_end] if desc_end > 0 else rest).strip(" -•—")
        date = _norm_date(date_raw)
        channel = _detect_channel(description)

        debit = credit = 0.0
        if amount_val < 0:
            amount_abs = abs(amount_val)
            if CREDIT_MARK.search(description):
                credit = amount_abs
            else:
                debit = amount_abs
        else:
            assigned = False
            if balance is not None and prev_balance is not None:
                delta = round(balance - prev_balance, 2)
                if abs(delta - amount_val) <= abs(delta + amount_val):
                    credit = amount_val
                else:
                    debit = amount_val
                assigned = True
            if not assigned:
                if CREDIT_MARK.search(description):
                    credit = amount_val
                elif DEBIT_MARK.search(description):
                    debit = amount_val
                else:
                    debit = amount_val

        txn = {
            "date": date,
            "description": description,
            "debit": debit if debit else 0.0,
            "credit": credit if credit else 0.0,
            "balance": balance,
        }
        if channel:
            txn["channel"] = channel
        result["transactions"].append(txn)

        if balance is not None:
            prev_balance = balance
        elif prev_balance is not None:
            prev_balance = round(prev_balance + credit - debit, 2)

    # totals
    txns = result["transactions"]
    result["totals"]["debits"] = round(sum(t["debit"] or 0.0 for t in txns), 2)
    result["totals"]["credits"] = round(sum(t["credit"] or 0.0 for t in txns), 2)
    result["totals"]["count"] = len(txns)

    # infer missing period
    if txns and (not result["period"]["start"] or not result["period"]["end"]):
        iso_dates = [t["date"] for t in txns if t["date"] and re.match(r"^\d{4}-\d{2}-\d{2}$", t["date"])]
        if iso_dates:
            result["period"]["start"] = min(iso_dates)
            result["period"]["end"] = max(iso_dates)
            result["statement"]["period"] = {"from": result["period"]["start"], "to": result["period"]["end"]}

    # closing balance fallback
    if result["closing_balance"] is None and txns:
        last_bal = next((t["balance"] for t in reversed(txns) if t["balance"] is not None), None)
        if last_bal is not None:
            result["closing_balance"] = last_bal

    result["totals"]["closing_balance"] = result["closing_balance"]

    # quality checks
    if len(txns) < 10:
        if "Parsed fewer than 10 transactions" not in result["warnings"]:
            result["warnings"].append("Parsed fewer than 10 transactions")
    if confidence is not None and confidence < 0.6:
        warning = f"Low classification confidence ({confidence:.2f})"
        if warning not in result["warnings"]:
            result["warnings"].append(warning)

    # balance drift check
    if txns:
        prev = result.get("opening_balance")
        drift = 0.0
        for txn in txns:
            debit = txn.get("debit") or 0.0
            credit = txn.get("credit") or 0.0
            balance = txn.get("balance")
            if prev is not None and balance is not None:
                expected = round(prev + credit - debit, 2)
                delta = abs(expected - balance)
                if delta > 1.0:
                    drift += delta
            if balance is not None:
                prev = balance
            elif prev is not None:
                prev = round(prev + credit - debit, 2)
        if drift > 1.0:
            warning = f"Balance drift detected (≈{drift:.2f})"
            if warning not in result["warnings"]:
                result["warnings"].append(warning)

    seen = set()
    deduped = []
    for w in result["warnings"]:
        if w not in seen:
            seen.add(w)
            deduped.append(w)
    result["warnings"] = deduped

    return result
