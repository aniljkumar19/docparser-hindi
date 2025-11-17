from __future__ import annotations

import re
from typing import Any, Callable, Dict


CHECKY = re.compile(r"\b(check|pos\s+purchase|atm|withdrawal)\b", re.IGNORECASE)


def interest_minor_amount(tr: Any, residual: float | None = None) -> bool:
    desc = (getattr(tr, "description", "") or "").lower()
    credit = getattr(tr, "credit", None)
    if credit is None:
        return False
    if "interest" in desc and "credit" in desc and credit >= 10:
        setattr(tr, "credit", round(float(credit) / 100.0, 2))
        return True
    return False


def fix_check_plus_50(tr: Any, residual: float | None = None) -> bool:
    if residual is None:
        return False
    debit = float(getattr(tr, "debit", 0.0) or 0.0)
    desc = getattr(tr, "description", "") or ""
    approx50 = 48.0 <= abs(residual) <= 52.0
    looks_debit = bool(CHECKY.search(desc)) or debit > 0
    small_amt = debit > 0 and debit < 10
    if approx50 and looks_debit and small_amt:
        adjustment = -residual
        setattr(tr, "debit", round(debit + adjustment, 2))
        return True
    return False


def join_neft_ref(tr: Any, residual: float | None = None) -> bool:
    desc = getattr(tr, "description", "")
    if not desc:
        return False
    # Collapse stray hyphen/newline artifacts often present in NEFT reference numbers.
    cleaned = re.sub(r"(\bNEFT\b[^\s]*)\s+([A-Z0-9]{6,})", r"\1-\2", desc, flags=re.IGNORECASE)
    if cleaned != desc:
        setattr(tr, "description", cleaned)
        return True
    return False


RULES_MAP: Dict[str, Callable[..., bool]] = {
    "interest_minor_amount": interest_minor_amount,
    "fix_check_plus_50": fix_check_plus_50,
    "join_neft_ref": join_neft_ref,
}

RESIDUAL_RULES = {"fix_check_plus_50"}

__all__ = ["RULES_MAP", "RESIDUAL_RULES"]

