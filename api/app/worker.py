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
from .recon.sales_vs_gstr1 import reconcile_sales_register_vs_gstr1

import json
import logging
logger = logging.getLogger(__name__)


def _attach_purchase_vs_gstr3b_recon(
    dbs, tenant_id: str | None, doc_type: str, result, meta: dict
):
    if not isinstance(result, dict):
        return

    # Use tenant_id if available, otherwise use empty string to match all jobs (for development)
    search_tenant_id = tenant_id if tenant_id else ""

    other_job = None
    if doc_type == "purchase_register":
        other_job = get_latest_job_by_doc_type(dbs, search_tenant_id, "gstr3b")
        pr_payload = result
        g3b_payload = getattr(other_job, "result", None) if other_job else None
        if not other_job:
            logger.debug(f"No GSTR-3B found for purchase_register reconciliation (tenant_id={search_tenant_id})")
    elif doc_type == "gstr3b":
        other_job = get_latest_job_by_doc_type(dbs, search_tenant_id, "purchase_register")
        pr_payload = getattr(other_job, "result", None) if other_job else None
        g3b_payload = result
        if not other_job:
            logger.debug(f"No purchase_register found for GSTR-3B reconciliation (tenant_id={search_tenant_id})")
    else:
        return

    if not pr_payload or not g3b_payload:
        logger.debug(f"Missing payloads for purchase vs GSTR-3B reconciliation: pr={bool(pr_payload)}, g3b={bool(g3b_payload)}")
        return

    try:
        recon = reconcile_pr_vs_gstr3b_itc(pr_payload, g3b_payload)
        if other_job:
            recon["paired_job_id"] = other_job.id
            recon["source_purchase_register_job_id"] = other_job.id if doc_type == "gstr3b" else None
            recon["source_purchase_register_filename"] = getattr(other_job, "filename", None) if doc_type == "gstr3b" else None
        recon["source_doc_type"] = doc_type
        meta.setdefault("reconciliations", {})["purchase_vs_gstr3b_itc"] = recon
        logger.info(f"Purchase vs GSTR-3B reconciliation attached for doc_type={doc_type}, tenant_id={tenant_id}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Purchase vs GSTR-3B reconciliation failed: {exc}")
        meta.setdefault("reconciliation_errors", []).append(str(exc))


def _attach_sales_vs_gstr1_recon(
    dbs, tenant_id: str | None, doc_type: str, result, meta: dict
):
    if not isinstance(result, dict):
        logger.debug(f"Sales vs GSTR-1 reconciliation skipped: result is not a dict (type: {type(result)})")
        return

    # Use tenant_id if available, otherwise use empty string to match all jobs (for development)
    search_tenant_id = tenant_id if tenant_id else ""
    logger.info(f"Attempting sales vs GSTR-1 reconciliation for doc_type={doc_type}, tenant_id={search_tenant_id}")

    other_job = None
    if doc_type == "sales_register":
        logger.info(f"Looking for GSTR-1 job for sales_register reconciliation (tenant_id={search_tenant_id})")
        other_job = get_latest_job_by_doc_type(dbs, search_tenant_id, "gstr1")
        sr_payload = result
        g1_payload = getattr(other_job, "result", None) if other_job else None
        if other_job:
            logger.info(f"Found GSTR-1 job {other_job.id} for sales_register reconciliation")
        else:
            logger.warning(f"No GSTR-1 found for sales_register reconciliation (tenant_id={search_tenant_id}, doc_type={doc_type})")
            # Try to find any GSTR-1 job regardless of tenant_id for debugging
            all_gstr1 = dbs.query(Job).filter(Job.doc_type == "gstr1", Job.status == "succeeded", Job.result.isnot(None)).order_by(Job.updated_at.desc()).limit(5).all()
            logger.info(f"Found {len(all_gstr1)} GSTR-1 jobs in database (any tenant_id): {[j.id for j in all_gstr1]}")
    elif doc_type == "gstr1":
        other_job = get_latest_job_by_doc_type(dbs, search_tenant_id, "sales_register")
        sr_payload = getattr(other_job, "result", None) if other_job else None
        g1_payload = result
        if not other_job:
            logger.warning(f"No sales_register found for GSTR-1 reconciliation (tenant_id={search_tenant_id}, doc_type={doc_type})")
            # Try to find any sales_register job regardless of tenant_id for debugging
            all_sr = dbs.query(Job).filter(Job.doc_type == "sales_register", Job.status == "succeeded", Job.result.isnot(None)).order_by(Job.updated_at.desc()).limit(5).all()
            logger.info(f"Found {len(all_sr)} sales_register jobs in database (any tenant_id): {[j.id for j in all_sr]}")
    else:
        logger.debug(f"Sales vs GSTR-1 reconciliation skipped: doc_type={doc_type} is not sales_register or gstr1")
        return

    if not sr_payload or not g1_payload:
        logger.warning(f"Missing payloads for sales vs GSTR-1 reconciliation: sr={bool(sr_payload)}, g1={bool(g1_payload)}, other_job={other_job.id if other_job else None}")
        return

    try:
        recon = reconcile_sales_register_vs_gstr1(sr_payload, g1_payload)
        if other_job:
            recon["source_sales_register_job_id"] = other_job.id if doc_type == "gstr1" else None
            recon["source_gstr1_job_id"] = other_job.id if doc_type == "sales_register" else None
            recon["source_sales_register_filename"] = getattr(other_job, "filename", None) if doc_type == "gstr1" else None
            recon["source_gstr1_filename"] = getattr(other_job, "filename", None) if doc_type == "sales_register" else None
        recon["source_doc_type"] = doc_type
        meta.setdefault("reconciliations", {})["sales_vs_gstr1"] = recon
        logger.info(f"Sales vs GSTR-1 reconciliation attached for doc_type={doc_type}, tenant_id={tenant_id}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Sales vs GSTR-1 reconciliation failed: {exc}")
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

            logger.info(f"Processing job {job_id}: doc_type={final_doc_type}, tenant_id={getattr(job, 'tenant_id', None)}")
            _attach_purchase_vs_gstr3b_recon(
                dbs, getattr(job, "tenant_id", None), final_doc_type, result, meta
            )
            _attach_sales_vs_gstr1_recon(
                dbs, getattr(job, "tenant_id", None), final_doc_type, result, meta
            )
            logger.info(f"Reconciliation complete for job {job_id}. Meta reconciliations: {list(meta.get('reconciliations', {}).keys())}")
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

