import os, time, json, requests
from datetime import datetime
from rq import Queue, Connection
import redis
from sqlalchemy.orm import Session
from .db import SessionLocal, init_db
from .models import Job, Usage, Webhook
from .storage import get_bytes
from .parsers.invoice_parser import extract_text_auto, parse_invoice_text

REDIS_URL = os.getenv("REDIS_URL","redis://localhost:6379/0")

def process_job(job_id: str):
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter_by(job_id=job_id).first()
        if not job:
            return
        data = get_bytes(job.storage_key)
        # We don't know the original filename; pass storage_key for type hint
        text, ocr_used = extract_text_auto(job.storage_key, data)
        result = parse_invoice_text(text or "")
        job.status = "succeeded"
        job.result = result
        job.meta = {"ocr_used": bool(ocr_used)}
        job.completed_at = datetime.utcnow()
        db.add(job)
        # Usage metering
        month = datetime.utcnow().strftime("%Y-%m")
        usage = db.query(Usage).filter_by(api_key=job.api_key, month=month).first()
        if not usage:
            usage = Usage(api_key=job.api_key, month=month, docs=0, ocr_pages=0)
        usage.docs += 1
        db.add(usage)
        db.commit()
        # webhook
        wh = db.query(Webhook).filter_by(api_key=job.api_key).first()
        if wh:
            try:
                requests.post(wh.url, json={
                    "job_id": job.job_id, "status": job.status, "doc_type": job.doc_type,
                    "result": job.result, "meta": job.meta
                }, timeout=2)
            except Exception:
                pass
    except Exception as e:
        try:
            job = db.query(Job).filter_by(job_id=job_id).first()
            if job:
                job.status = "failed"
                job.meta = {"error": str(e)}
                db.add(job); db.commit()
        except Exception:
            pass
    finally:
        db.close()

if __name__ == "__main__":
    # Worker entrypoint
    init_db()
    r = redis.from_url(REDIS_URL)
    with Connection(r):
        q = Queue("doc-jobs")
        # Simple work loop (poll)
        print("Worker started. Polling queue...")
        while True:
            job = q.dequeue()
            if job:
                args, kwargs = job.args, job.kwargs
                process_job(*args, **kwargs)
            time.sleep(1)
