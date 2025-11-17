from .db import (
    SessionLocal,
    get_job_by_id,
    update_job_status,
    get_metered_item_for_tenant,
    get_latest_job_by_doc_type,
)
from .storage import get_file_from_s3
from .parsers.invoice import parse_bytes_to_result
from .billing.stripe_billing import record_usage
from .parsers.router import parse_any
from .parsers.common import extract_text_safely, extract_text_with_layout
from .parsers.gstr3b import normalize_gstr3b
from .recon.purchase_vs_gstr3b import reconcile_pr_vs_gstr3b_itc
from .parsers.gstr1 import normalize_gstr1

import json
import logging
logger = logging.getLogger(__name__)


def _attach_purchase_vs_gstr3b_recon(
    dbs, tenant_id: str | None, doc_type: str, result, meta: dict
):
    if not tenant_id or not isinstance(result, dict):
        return

    other_job = None
    if doc_type == "purchase_register":
        other_job = get_latest_job_by_doc_type(dbs, tenant_id, "gstr3b")
        pr_payload = result
        g3b_payload = getattr(other_job, "result", None) if other_job else None
    elif doc_type == "gstr3b":
        other_job = get_latest_job_by_doc_type(dbs, tenant_id, "purchase_register")
        pr_payload = getattr(other_job, "result", None) if other_job else None
        g3b_payload = result
    else:
        return

    if not pr_payload or not g3b_payload:
        return

    try:
        recon = reconcile_pr_vs_gstr3b_itc(pr_payload, g3b_payload)
        if other_job:
            recon["paired_job_id"] = other_job.id
        recon["source_doc_type"] = doc_type
        meta.setdefault("reconciliations", {})["purchase_vs_gstr3b_itc"] = recon
    except Exception as exc:  # noqa: BLE001
        meta.setdefault("reconciliation_errors", []).append(str(exc))


def parse_job_task(job_id: str):
    dbs = SessionLocal()
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if not job:
            return
        update_job_status(dbs, job_id, status="processing")
        try:
            data = get_file_from_s3(job.object_key)
            fn = getattr(job, "filename", None) or "document"

            job_meta = {}
            if isinstance(job.meta, dict):
                job_meta = dict(job.meta)
            elif isinstance(job.meta, str):
                try:
                    job_meta = json.loads(job.meta)
                except Exception:
                    job_meta = {}

            requested_doc_type = (job_meta or {}).get("requested_doc_type")

            result, meta = parse_any(fn, data, forced_doc_type=requested_doc_type)
            meta = dict(meta or {})
            meta.setdefault("source_filename", fn)
            if requested_doc_type:
                meta.setdefault("requested_doc_type", requested_doc_type)

            final_doc_type = requested_doc_type or meta.get("detected_doc_type") or meta.get("doc_type_internal") or "invoice"

            job_status = "succeeded"
            quality = meta.get("invoice_quality") if isinstance(meta, dict) else None
            if final_doc_type in ("invoice", "gst_invoice") and isinstance(quality, dict):
                if not quality.get("is_usable"):
                    job_status = "needs_review"
                    if isinstance(result, dict):
                        warnings = result.setdefault("warnings", [])
                        warnings.append("invoice_low_coverage")

            if final_doc_type == "gstr":
                gstr_form = (result.get("gstr_form") or {}).get("value", "").upper() if isinstance(result, dict) else ""
                if gstr_form in {"GSTR-3B", "GSTR-1"}:
                    layout_text = extract_text_with_layout(data) or extract_text_safely(data, fn)[0]
                    if gstr_form == "GSTR-3B" and normalize_gstr3b:
                        result = normalize_gstr3b(layout_text or "")
                        meta["detected_doc_type"] = "gstr3b"
                        final_doc_type = "gstr3b"
                    elif gstr_form == "GSTR-1" and normalize_gstr1:
                        result = normalize_gstr1(layout_text or "")
                        meta["detected_doc_type"] = "gstr1"
                        final_doc_type = "gstr1"
                    meta["text_content"] = layout_text

            _attach_purchase_vs_gstr3b_recon(
                dbs, getattr(job, "tenant_id", None), final_doc_type, result, meta
            )
            update_job_status(
                dbs,
                job_id,
                status=job_status,
                result=result,
                meta=meta,
                doc_type=final_doc_type,
            )
            try:
                if getattr(job, "tenant_id", None):
                    item = get_metered_item_for_tenant(dbs, job.tenant_id)  # should return 'si_...'
                    if item:
                        record_usage(item, units=1, job_id=job_id)  # idempotent by job_id
                        logger.info("BILLING usage recorded for %s -> %s", job.tenant_id, item)
                    else:
                        logger.info("BILLING skipped: no metered item for tenant %s", job.tenant_id)
            except Exception as e:
                logger.warning("BILLING error (non-fatal): %s", e)
        except Exception as e:
            update_job_status(dbs, job_id, status="failed", result=None, meta={"error": str(e)})

