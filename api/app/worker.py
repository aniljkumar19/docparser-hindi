from .db import (
    SessionLocal,
    get_job_by_id,
    update_job_status,
    get_metered_item_for_tenant,
    get_latest_job_by_doc_type,
    find_matching_job_by_gstin_and_period,
)
# Import helper functions for GSTIN and period extraction
from .db import _normalize_gstin, _extract_gstin_from_result, _extract_period_from_result
from .storage import get_file_from_s3
from .parsers.invoice import parse_bytes_to_result
from .billing.stripe_billing import record_usage
from .parsers.router import parse_any
from .parsers.common import extract_text_safely, extract_text_with_layout
from .parsers.gstr3b import normalize_gstr3b
from .recon.purchase_vs_gstr3b import reconcile_pr_vs_gstr3b_itc
from .parsers.gstr1 import normalize_gstr1
from .recon.sales_vs_gstr1 import reconcile_sales_register_vs_gstr1
from .recon.itc_2b_3b import reconcile_itc_2b_3b
from .parsers.canonical import normalize_to_canonical

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

    # Extract GSTIN and period from current document for smart matching
    source_gstin = _extract_gstin_from_result(result)
    source_period_month, source_period_year = _extract_period_from_result(result)
    
    logger.info(f"Purchase vs GSTR-3B reconciliation: source_gstin={source_gstin}, period={source_period_month}/{source_period_year}")
    
    other_job = None
    if doc_type == "purchase_register":
        logger.info(f"Looking for GSTR-3B job matching GSTIN={source_gstin}, period={source_period_month}/{source_period_year}")
        # Use smart matching: find by GSTIN and period
        if source_gstin and source_period_month and source_period_year:
            other_job = find_matching_job_by_gstin_and_period(
                dbs, search_tenant_id, "gstr3b",
                source_gstin, source_period_month, source_period_year
            )
        # Fallback to simple doc_type matching if no GSTIN/period
        if not other_job:
            logger.info("Falling back to simple doc_type matching (no GSTIN/period available)")
            other_job = get_latest_job_by_doc_type(dbs, search_tenant_id, "gstr3b")
        
        pr_payload = result
        g3b_payload = getattr(other_job, "result", None) if other_job else None
        if other_job:
            other_gstin = _extract_gstin_from_result(other_job.result)
            other_period = _extract_period_from_result(other_job.result)
            logger.info(f"Found GSTR-3B job {other_job.id} (GSTIN={other_gstin}, period={other_period[0]}/{other_period[1]})")
        else:
            logger.warning(f"No matching GSTR-3B found for purchase_register (GSTIN={source_gstin}, period={source_period_month}/{source_period_year})")
    elif doc_type == "gstr3b":
        logger.info(f"Looking for purchase_register job matching GSTIN={source_gstin}, period={source_period_month}/{source_period_year}")
        # Use smart matching: find by GSTIN and period
        if source_gstin and source_period_month and source_period_year:
            other_job = find_matching_job_by_gstin_and_period(
                dbs, search_tenant_id, "purchase_register",
                source_gstin, source_period_month, source_period_year
            )
        # Fallback to simple doc_type matching if no GSTIN/period
        if not other_job:
            logger.info("Falling back to simple doc_type matching (no GSTIN/period available)")
            other_job = get_latest_job_by_doc_type(dbs, search_tenant_id, "purchase_register")
        
        pr_payload = getattr(other_job, "result", None) if other_job else None
        g3b_payload = result
        if other_job:
            other_gstin = _extract_gstin_from_result(other_job.result)
            other_period = _extract_period_from_result(other_job.result)
            logger.info(f"Found purchase_register job {other_job.id} (GSTIN={other_gstin}, period={other_period[0]}/{other_period[1]})")
        else:
            logger.warning(f"No matching purchase_register found for GSTR-3B (GSTIN={source_gstin}, period={source_period_month}/{source_period_year})")
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


def _attach_itc_2b_3b_recon(
    dbs, tenant_id: str | None, doc_type: str, result, meta: dict
):
    """
    Attach ITC reconciliation (GSTR-2B vs GSTR-3B) using canonical format.
    
    This reconciliation compares:
    - GSTR-2B: ITC available (from financials.tax_breakup)
    - GSTR-3B: ITC claimed (from doc_specific.input_tax_credit.total)
    """
    if not isinstance(result, dict):
        return
    
    # Only process if this is a GSTR-2B or GSTR-3B document
    if doc_type not in ("gstr2b", "gstr3b"):
        return
    
    # Use tenant_id if available, otherwise use empty string to match all jobs (for development)
    search_tenant_id = tenant_id if tenant_id else ""
    
    # Extract GSTIN and period from current document for smart matching
    source_gstin = _extract_gstin_from_result(result)
    source_period_month, source_period_year = _extract_period_from_result(result)
    
    logger.info(f"ITC 2B vs 3B reconciliation: source_gstin={source_gstin}, period={source_period_month}/{source_period_year}, doc_type={doc_type}")
    
    other_job = None
    if doc_type == "gstr2b":
        logger.info(f"Looking for GSTR-3B job matching GSTIN={source_gstin}, period={source_period_month}/{source_period_year}")
        # Use smart matching: find by GSTIN and period
        if source_gstin and source_period_month and source_period_year:
            other_job = find_matching_job_by_gstin_and_period(
                dbs, search_tenant_id, "gstr3b",
                source_gstin, source_period_month, source_period_year
            )
        # Fallback to simple doc_type matching if no GSTIN/period
        if not other_job:
            logger.info("Falling back to simple doc_type matching (no GSTIN/period available)")
            other_job = get_latest_job_by_doc_type(dbs, search_tenant_id, "gstr3b")
        
        gstr2b_payload = result
        gstr3b_payload = getattr(other_job, "result", None) if other_job else None
        if other_job:
            other_gstin = _extract_gstin_from_result(other_job.result)
            other_period = _extract_period_from_result(other_job.result)
            logger.info(f"Found GSTR-3B job {other_job.id} (GSTIN={other_gstin}, period={other_period[0]}/{other_period[1]})")
        else:
            logger.warning(f"No matching GSTR-3B found for GSTR-2B (GSTIN={source_gstin}, period={source_period_month}/{source_period_year})")
    elif doc_type == "gstr3b":
        logger.info(f"Looking for GSTR-2B job matching GSTIN={source_gstin}, period={source_period_month}/{source_period_year}")
        # Use smart matching: find by GSTIN and period
        if source_gstin and source_period_month and source_period_year:
            other_job = find_matching_job_by_gstin_and_period(
                dbs, search_tenant_id, "gstr2b",
                source_gstin, source_period_month, source_period_year
            )
        # Fallback to simple doc_type matching if no GSTIN/period
        if not other_job:
            logger.info("Falling back to simple doc_type matching (no GSTIN/period available)")
            other_job = get_latest_job_by_doc_type(dbs, search_tenant_id, "gstr2b")
        
        gstr2b_payload = getattr(other_job, "result", None) if other_job else None
        gstr3b_payload = result
        if other_job:
            other_gstin = _extract_gstin_from_result(other_job.result)
            other_period = _extract_period_from_result(other_job.result)
            logger.info(f"Found GSTR-2B job {other_job.id} (GSTIN={other_gstin}, period={other_period[0]}/{other_period[1]})")
        else:
            logger.warning(f"No matching GSTR-2B found for GSTR-3B (GSTIN={source_gstin}, period={source_period_month}/{source_period_year})")
    else:
        return
    
    if not gstr2b_payload or not gstr3b_payload:
        logger.debug(f"Missing payloads for ITC 2B vs 3B reconciliation: 2b={bool(gstr2b_payload)}, 3b={bool(gstr3b_payload)}")
        return
    
    try:
        # Convert both to canonical format for reconciliation
        canonical_2b = normalize_to_canonical("gstr2b", gstr2b_payload)
        canonical_3b = normalize_to_canonical("gstr3b", gstr3b_payload)
        
        # Perform reconciliation
        recon = reconcile_itc_2b_3b(canonical_2b, canonical_3b)
        
        if other_job:
            recon["paired_job_id"] = other_job.id
            recon["source_gstr2b_job_id"] = other_job.id if doc_type == "gstr3b" else None
            recon["source_gstr3b_job_id"] = other_job.id if doc_type == "gstr2b" else None
            recon["source_gstr2b_filename"] = getattr(other_job, "filename", None) if doc_type == "gstr3b" else None
            recon["source_gstr3b_filename"] = getattr(other_job, "filename", None) if doc_type == "gstr2b" else None
        recon["source_doc_type"] = doc_type
        
        meta.setdefault("reconciliations", {})["itc_2b_3b"] = recon
        logger.info(f"ITC 2B vs 3B reconciliation attached for doc_type={doc_type}, tenant_id={tenant_id}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"ITC 2B vs 3B reconciliation failed: {exc}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
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

    # Extract GSTIN and period from current document for smart matching
    source_gstin = _extract_gstin_from_result(result)
    source_period_month, source_period_year = _extract_period_from_result(result)
    
    logger.info(f"Sales vs GSTR-1 reconciliation: source_gstin={source_gstin}, period={source_period_month}/{source_period_year}")
    
    other_job = None
    if doc_type == "sales_register":
        logger.info(f"Looking for GSTR-1 job matching GSTIN={source_gstin}, period={source_period_month}/{source_period_year}")
        # Use smart matching: find by GSTIN and period
        if source_gstin and source_period_month and source_period_year:
            other_job = find_matching_job_by_gstin_and_period(
                dbs, search_tenant_id, "gstr1", 
                source_gstin, source_period_month, source_period_year
            )
        # Fallback to simple doc_type matching if no GSTIN/period
        if not other_job:
            logger.info("Falling back to simple doc_type matching (no GSTIN/period available)")
            other_job = get_latest_job_by_doc_type(dbs, search_tenant_id, "gstr1")
        
        sr_payload = result
        g1_payload = getattr(other_job, "result", None) if other_job else None
        if other_job:
            other_gstin = _extract_gstin_from_result(other_job.result)
            other_period = _extract_period_from_result(other_job.result)
            logger.info(f"Found GSTR-1 job {other_job.id} (GSTIN={other_gstin}, period={other_period[0]}/{other_period[1]})")
        else:
            logger.warning(f"No matching GSTR-1 found for sales_register (GSTIN={source_gstin}, period={source_period_month}/{source_period_year})")
    elif doc_type == "gstr1":
        logger.info(f"Looking for sales_register job matching GSTIN={source_gstin}, period={source_period_month}/{source_period_year}")
        # Use smart matching: find by GSTIN and period
        if source_gstin and source_period_month and source_period_year:
            other_job = find_matching_job_by_gstin_and_period(
                dbs, search_tenant_id, "sales_register",
                source_gstin, source_period_month, source_period_year
            )
        # Fallback to simple doc_type matching if no GSTIN/period
        if not other_job:
            logger.info("Falling back to simple doc_type matching (no GSTIN/period available)")
            other_job = get_latest_job_by_doc_type(dbs, search_tenant_id, "sales_register")
        
        sr_payload = getattr(other_job, "result", None) if other_job else None
        g1_payload = result
        if other_job:
            other_gstin = _extract_gstin_from_result(other_job.result)
            other_period = _extract_period_from_result(other_job.result)
            logger.info(f"Found sales_register job {other_job.id} (GSTIN={other_gstin}, period={other_period[0]}/{other_period[1]})")
        else:
            logger.warning(f"No matching sales_register found for GSTR-1 (GSTIN={source_gstin}, period={source_period_month}/{source_period_year})")
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

            parse_result = parse_any(fn, data, forced_doc_type=requested_doc_type)
            # parse_any returns (result, meta, doc_type) for JSON files, (result, meta) for others
            # Handle both cases for backward compatibility
            try:
                if isinstance(parse_result, tuple) and len(parse_result) == 3:
                    result, meta, detected_doc_type = parse_result
                else:
                    result, meta = parse_result
                    detected_doc_type = None
            except (ValueError, TypeError):
                # Fallback: try to unpack as 2 values
                result, meta = parse_result[:2] if isinstance(parse_result, (tuple, list)) else (parse_result, {})
                detected_doc_type = None
            
            meta = dict(meta or {})
            meta.setdefault("source_filename", fn)
            if requested_doc_type:
                meta.setdefault("requested_doc_type", requested_doc_type)
            if detected_doc_type:
                meta.setdefault("detected_doc_type", detected_doc_type)

            final_doc_type = requested_doc_type or detected_doc_type or meta.get("detected_doc_type") or meta.get("doc_type_internal") or "invoice"
            
            # Fallback: if filename suggests GSTR-1 but detection failed, force re-check
            fn_lower = fn.lower()
            if not requested_doc_type and ("gstr1" in fn_lower or "gstr-1" in fn_lower or "gstr_1" in fn_lower):
                if final_doc_type == "invoice" and isinstance(result, dict):
                    # Try to detect GSTR form from result or re-parse as GSTR
                    logger.warning(f"GSTR-1 filename detected but doc_type is {final_doc_type}. Attempting GSTR-1 normalization.")
                    try:
                        layout_text = extract_text_with_layout(data) or extract_text_safely(data, fn)[0]
                        if normalize_gstr1:
                            gstr1_result = normalize_gstr1(layout_text or "")
                            if isinstance(gstr1_result, dict) and gstr1_result.get("doc_type") == "gstr1":
                                result = gstr1_result
                                meta["detected_doc_type"] = "gstr1"
                                final_doc_type = "gstr1"
                                logger.info(f"Successfully normalized as GSTR-1 from filename hint")
                    except Exception as e:
                        logger.warning(f"Failed to normalize as GSTR-1 from filename: {e}")
            elif not requested_doc_type and "sales" in fn_lower and ("register" in fn_lower or "csv" in fn_lower):
                if final_doc_type != "sales_register" and isinstance(result, dict):
                    logger.warning(f"Sales register filename detected but doc_type is {final_doc_type}. Attempting sales_register normalization.")
                    try:
                        from .parsers.sales_register import normalize_sales_register
                        if normalize_sales_register:
                            cleaned_text = extract_text_safely(data, fn)[0]
                            sr_result = normalize_sales_register(cleaned_text)
                            if isinstance(sr_result, dict) and sr_result.get("doc_type") == "sales_register":
                                result = sr_result
                                meta["detected_doc_type"] = "sales_register"
                                final_doc_type = "sales_register"
                                logger.info(f"Successfully normalized as sales_register from filename hint")
                    except Exception as e:
                        logger.warning(f"Failed to normalize as sales_register from filename: {e}")

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
            _attach_itc_2b_3b_recon(
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

