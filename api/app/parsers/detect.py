# api/app/parsers/detect.py
import re

KEYS = {
    # REMOVE subtotal/total from invoice signals
    "invoice": [
        r"\binvoice\b", r"\btax invoice\b", r"\bgstin\b", r"\bbill to\b", r"\binvoice (no|#)\b",
        # Hindi patterns: चालान, बिल, कर चालान, टैक्स इनवॉइस
        r"चालान", r"बिल", r"कर\s*चालान", r"टैक्स\s*इनवॉइस", r"जीएसटी\s*चालान"
    ],
    "birth_certificate": [r"\bbirth certificate\b", r"\bdate of birth\b", r"\bplace of birth\b"],
    # Indian document types
    "eway_bill": [
        r"\beway bill\b", r"\bway bill\b", r"\btransport document\b", r"\bvehicle no\b", r"\btransporter\b",
        # Hindi: ई-वे बिल, वे बिल
        r"ई[-\s]*वे\s*बिल", r"वे\s*बिल"
    ],
    "gstr": [
        r"\bgstr\b", r"\bgst return\b", r"\bgst filing\b", r"\bturnover\b", r"\btaxable value\b",
        # Hindi: जीएसटी रिटर्न, जीएसटी दाखिल
        r"जीएसटी\s*रिटर्न", r"जीएसटी\s*दाखिल"
    ],
    "purchase_register": [
        r"\bpurchase register\b",
        r"\bsupplier gstin\b",
        r"\bpurchase invoice\b",
        r"\bpurchase value\b",
        # Hindi: खरीद रजिस्टर, आपूर्तिकर्ता
        r"खरीद\s*रजिस्टर", r"आपूर्तिकर्ता"
    ],
}
RECEIPT_HINTS = ("thank you", "cashier", "pos", "tender", "change", "subtotal", "receipt", "store #", "terminal")

# add utility bill signals
UTILITY_HINTS = (
    "amount due", "total due", "balance due",
    "service period", "bill date", "due date", "tariff", "meter", "kwh"
)

# add gstr hints
GSTR_HINTS = (
    "form gstr-1",
    "form gstr-3b",
    "form gstr-2b",
    "gstr-1",
    "gstr-3b",
    "gstr 1",
    "gstr 3b",
    "gst return",
    "gst summary",
    "gst portal",
    "gst.gov.in",
    "gstn",
    "arn:",
    "acknowledgement reference number",
    "outward supplies",
    "taxable value",
)

# add with your other hint groups
BANK_HINTS = (
    "bank statement",
    "statement of account",
    "opening balance",
    "closing balance",
    "neft",
    "rtgs",
    "imps",
    "upi",
    "narration",
    "txn id",
    "cheque",
    "withdrawal",
    "deposit",
)

BANK_PATTERNS = [
    r"statement\s+period",
    r"\bmicr\b",
    r"\bdate\b.*\b(narration|description)\b.*\bdebit\b.*\bcredit\b.*\bbalance\b",
    r"\b(neft|imps|upi|rtgs|cheque)\b",
    r"(opening|closing)\s+balance",
    r"\bbranch\b",
]

def score_bank_statement(text: str) -> tuple[int, float]:
    hits = sum(1 for p in BANK_PATTERNS if re.search(p, text, re.I | re.S))
    conf = min(1.0, hits / 8.0)
    return hits, conf


def detect_doc_type_with_scores(text: str) -> tuple[str, dict, dict]:
    low = (text or "").lower()
    scores = {k: 0 for k in KEYS}
    scores.setdefault("receipt", 0)
    scores.setdefault("utility_bill", 0)
    scores.setdefault("bank_statement", 0)
    scores.setdefault("eway_bill", 0)
    scores.setdefault("gstr", 0)
    confidences = {k: 0.0 for k in scores}

    for t, pats in (globals().get("KEYS") or {}).items():
        for p in pats:
            if re.search(p, low):
                scores[t] += 1

    # receipt heuristics
    if any(h in low for h in RECEIPT_HINTS):
        scores["receipt"] += 2
    if low.count("\n") > 10 and "total" in low and "invoice" not in low:
        scores["receipt"] += 1

    # utility bill heuristics
    if any(h in low for h in UTILITY_HINTS):
        scores["utility_bill"] += 2

    # sales register heuristics
    if "sales register" in low or "sales summary" in low:
        scores.setdefault("sales_register", 0)
        scores["sales_register"] += 4
    if "customer gstin" in low and "invoice value" in low:
        scores.setdefault("sales_register", 0)
        scores["sales_register"] += 2

    # purchase register heuristics
    if "purchase register" in low:
        scores["purchase_register"] += 4
    if "supplier gstin" in low and "invoice value" in low:
        scores["purchase_register"] += 2
    if "purchase value" in low and "taxable value" in low:
        scores["purchase_register"] += 1

    # gstr hints
    gstr_hits = sum(1 for h in GSTR_HINTS if h in low)
    if gstr_hits:
        scores["gstr"] += gstr_hits * 2
        if gstr_hits >= 2:
            scores["gstr"] += 2
            scores["bank_statement"] = max(0, scores["bank_statement"] - gstr_hits)
    
    # new: bank hints
    bank_hits = sum(1 for h in BANK_HINTS if h in low)
    if bank_hits >= 1:
        scores["bank_statement"] += 2
    if "opening balance" in low and "closing balance" in low:
        scores["bank_statement"] += 2
    if sum(1 for h in ("neft","rtgs","imps","upi","cheque") if h in low) >= 2:
        scores["bank_statement"] += 1
    if "account number" in low or "statement period" in low:
        scores["bank_statement"] += 1

    hits, bank_conf = score_bank_statement(text)
    if hits:
        scores["bank_statement"] += hits * 2
        confidences["bank_statement"] = max(confidences.get("bank_statement", 0.0), bank_conf)

    best = max(scores, key=scores.get)
    if scores.get("gstr", 0) >= scores.get("bank_statement", 0) + 2 and scores.get("gstr", 0) >= 3:
        best = "gstr"
    elif best == "bank_statement" and scores.get("bank_statement", 0) >= scores.get(best, 0):
        best = "bank_statement"

    if best == "bank_statement" and scores.get("bank_statement", 0) >= 3:
        scores["receipt"] = 0
        confidences["receipt"] = 0.0

    if scores.get(best, 0) <= 0:
        return "unknown", scores, confidences

    # derive default confidences based on score magnitude
    for key, value in scores.items():
        if value <= 0:
            continue
        confidences[key] = max(confidences.get(key, 0.0), min(1.0, value / 5.0))

    return best, scores, confidences

def detect_doc_type(text: str) -> str:
    low = (text or "").lower()

    # ensure 'receipt' is scored too
    scores = {k: 0 for k in KEYS}
    scores["receipt"] = 0

    for t, pats in KEYS.items():
        for p in pats:
            if re.search(p, low):
                scores[t] += 1

    # receipt heuristics
    if any(h in low for h in RECEIPT_HINTS):
        scores["receipt"] += 2
    if low.count("\n") > 10 and "total" in low and "invoice" not in low:
        scores["receipt"] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"

