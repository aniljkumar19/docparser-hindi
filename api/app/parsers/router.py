# api/app/parsers/router.py
import time
from typing import Any, Dict

from .common import extract_text_safely, normalize_text
#from .detect import detect_doc_type
from .detect import detect_doc_type_with_scores
from .invoice import parse_text_rules as parse_invoice
try:
    from .receipt import parse_text_rules as parse_receipt
except Exception:
    parse_receipt = None
try:
    from .utility_bill import parse_text_rules as parse_ubill
except Exception:
    parse_ubill = None
try:
    from .bank_statement import parse_text_rules as parse_bank
except Exception:
    parse_bank = None
try:
    from .bank_normalizer import normalize_bank_statement
except Exception:
    normalize_bank_statement = None
try:
    from .eway_bill import parse_text_rules as parse_eway
except Exception:
    parse_eway = None
try:
    from .gstr import parse_text_rules as parse_gstr, gstr_quality_score
except Exception:
    parse_gstr = None
    gstr_quality_score = None
try:
    from .gstr3b import normalize_gstr3b
except Exception:
    normalize_gstr3b = None
try:
    from .gstr1 import normalize_gstr1
except Exception:
    normalize_gstr1 = None
try:
    from .gst_invoice import parse_text_rules as parse_gst_invoice
except Exception:
    parse_gst_invoice = None
try:
    from .purchase_register import normalize_purchase_register
except Exception:
    normalize_purchase_register = None
try:
    from .sales_register import normalize_sales_register
except Exception:
    normalize_sales_register = None
try:
    from .policy_loader import load_policy, pick_bank_profile
except Exception:
    load_policy = None
    pick_bank_profile = None
try:
    from .invoice_helpers import apply_invoice_fallbacks, evaluate_invoice_quality
except Exception:
    apply_invoice_fallbacks = None
    evaluate_invoice_quality = None

SUPPORTED_DOC_TYPES = {
    "invoice",
    "gst_invoice",
    "receipt",
    "utility_bill",
    "bank_statement",
    "eway_bill",
    "gstr",
    "gstr3b",
    "gstr1",
    "purchase_register",
    "sales_register",
}
DOC_TYPE_ALIASES = {
    "gst_return": "gstr",
    "gst_form": "gstr",
    "gst": "gst_invoice",
    "gstr-3b": "gstr3b",
    "gstr3b": "gstr3b",
    "gstr-1": "gstr1",
    "gstr1": "gstr1",
    "purchase_register": "purchase_register",
    "purchase-register": "purchase_register",
    "sales_register": "sales_register",
    "sales-register": "sales_register",
}

BANK_POLICY = {}
if load_policy:
    try:
        BANK_POLICY = load_policy()
    except Exception:
        BANK_POLICY = {}

def _unknown_result():
    return {
        "invoice_number": None, "date": None,
        "seller": {}, "buyer": {}, "currency": None,
        "subtotal": None, "taxes": [], "total": None, "line_items": [],
        "warnings": ["Unsupported or unknown document type"]
    }


def _resolve_forced_doc_type(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    label = value.strip().lower()
    route = DOC_TYPE_ALIASES.get(label, label)
    if route not in SUPPORTED_DOC_TYPES:
        return None, None
    return label, route


def parse_any(filename: str, data: bytes, forced_doc_type: str | None = None):
    t0 = time.time()
    raw_text, ocr_used = extract_text_safely(data, filename)
    cleaned_text = normalize_text(raw_text)
    text_len = len(cleaned_text)
    page1_text = (raw_text or "").split("\f", 1)[0]

    forced_label, forced_internal = _resolve_forced_doc_type(forced_doc_type)
    meta_forced = bool(forced_internal)

    if forced_internal:
        doc_type = forced_internal
        display_doc_type = forced_label or forced_internal
        scores = {display_doc_type: 5}
        confidences = {display_doc_type: 1.0}
        conf = 1.0
    else:
        doc_type, scores, confidences = detect_doc_type_with_scores(cleaned_text)
        conf = confidences.get(doc_type, 0.0)
        if conf < 0.35:
            doc_type = "unknown"
        display_doc_type = doc_type

    normalized = None
    meta_extra: Dict[str, Any] = {}

    if doc_type == "invoice":
        result = parse_invoice(cleaned_text)
        if apply_invoice_fallbacks:
            result = apply_invoice_fallbacks(result, raw_text or cleaned_text)
    elif doc_type == "gst_invoice" and parse_gst_invoice:
        result = parse_gst_invoice(cleaned_text)
        if apply_invoice_fallbacks:
            result = apply_invoice_fallbacks(result, raw_text or cleaned_text)
    elif doc_type == "receipt" and parse_receipt:
        result = parse_receipt(cleaned_text)
    elif doc_type == "utility_bill" and parse_ubill:
        result = parse_ubill(cleaned_text)
    elif doc_type == "bank_statement" and parse_bank:
        result = parse_bank(cleaned_text, confidence=conf)
        if normalize_bank_statement and isinstance(result, dict):
            profile = None
            if pick_bank_profile:
                try:
                    profile = pick_bank_profile(page1_text, BANK_POLICY)
                except Exception:
                    profile = None

            normalized = normalize_bank_statement(
                ocr_text=raw_text or "",
                transactions=result.get("transactions") or [],
                opening_balance=result.get("opening_balance"),
                closing_balance=result.get("closing_balance"),
                profile=profile,
            )

            result["transactions"] = normalized.transactions
            result["totals"] = normalized.totals
            result["opening_balance"] = normalized.opening_balance
            result["closing_balance"] = normalized.closing_balance

            result.setdefault("statement", {})
            result["statement"]["period"] = {
                "from": normalized.period_start,
                "to": normalized.period_end,
            }
            result["period"] = {
                "start": normalized.period_start,
                "end": normalized.period_end,
            }

            result.setdefault("warnings", [])
            result["warnings"] = [
                w for w in result["warnings"] if "Balance drift detected" not in w
            ]
            result["warnings"].extend(normalized.warnings)
            seen_warnings = set()
            deduped = []
            for item in result["warnings"]:
                if item not in seen_warnings:
                    seen_warnings.add(item)
                    deduped.append(item)
            result["warnings"] = deduped

            meta_period = {
                "from": normalized.period_start,
                "to": normalized.period_end,
            }
            meta_extra = {
                "normalized_transaction_count": normalized.totals.get("count", 0),
                "statement_period": meta_period,
                "bank_profile": normalized.profile_name,
                "reconciliation_rate": normalized.reconciliation_rate,
                "closing_drift": normalized.closing_drift,
            }
            result.setdefault("meta", {})
            result["meta"].update(
                {
                    "bank_profile": normalized.profile_name,
                    "reconciliation_rate": normalized.reconciliation_rate,
                    "closing_drift": normalized.closing_drift,
                }
            )
        else:
            normalized = None
    elif doc_type == "eway_bill" and parse_eway:
        result = parse_eway(cleaned_text)
    elif doc_type == "gstr" and parse_gstr:
        result = parse_gstr(cleaned_text)
        if isinstance(result, dict) and gstr_quality_score:
            quality = gstr_quality_score(result)
            if quality < 3:
                result.setdefault("warnings", []).append("Low coverage – likely wrong doc type.")
                meta_extra["gstr_low_coverage"] = True
    elif doc_type == "gstr3b" and normalize_gstr3b:
        normalized = normalize_gstr3b(raw_text or "")
        parser_meta = normalized.get("meta")
        if parser_meta:
            meta_extra.update({f"gstr3b_{k}": v for k, v in parser_meta.items()})
        result = normalized
    elif doc_type == "gstr1" and normalize_gstr1:
        result = normalize_gstr1(raw_text or "")
    elif doc_type == "purchase_register" and normalize_purchase_register:
        result = normalize_purchase_register(cleaned_text)
    elif doc_type == "sales_register" and normalize_sales_register:
        result = normalize_sales_register(cleaned_text)
    else:
        doc_type = "unknown"
        display_doc_type = doc_type
        result = _unknown_result()

    if doc_type in ("invoice", "gst_invoice") and isinstance(result, dict) and evaluate_invoice_quality:
        quality = evaluate_invoice_quality(result)
        meta_extra["invoice_quality"] = quality

    if doc_type == "bank_statement" and isinstance(result, dict):
        txns = result.get("transactions", [])
        if len(txns) < 10:
            result.setdefault("warnings", []).append("Parsed fewer than 10 transactions")
        if conf < 0.6:
            result.setdefault("warnings", []).append(f"Low classification confidence ({conf:.2f})")
        if len(txns) < 5:
            result.setdefault("warnings", []).append("Too few transactions – likely wrong document type.")
            meta_extra["reconciliation_rate"] = None
            meta_extra["closing_drift"] = None

    if doc_type != "bank_statement" and conf < 0.4:
        result.setdefault("warnings", []).append(f"Low classification confidence ({conf:.2f})")

    text_source = "ocr" if ocr_used else "pdf_text"
    if not ocr_used and not (filename and filename.lower().endswith(".pdf")) and not data.startswith(b"%PDF"):
        text_source = "plain_text"

    meta = {
        "pages": 1,
        "ocr_used": ocr_used,
        "processing_ms": int((time.time() - t0) * 1000),
        "detected_doc_type": display_doc_type,
        "doc_type_scores": scores,
        "doc_type_confidence": conf,
        "doc_type_confidences": confidences,
        "text_source": text_source,
        "text_len": text_len,
    }
    meta["doc_type_internal"] = doc_type
    if meta_forced:
        meta["doc_type_forced"] = True
        if forced_label:
            meta.setdefault("requested_doc_type", forced_label)

    if meta_extra:
        meta.update(meta_extra)
    if doc_type == "bank_statement" and normalized:
        meta["balance_warnings"] = normalized.warnings
    return result, meta
