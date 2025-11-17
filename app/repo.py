import json, time
from sqlalchemy.orm import Session
from .models import Job, Usage, Webhook

def month_now() -> str:
    return time.strftime("%Y-%m")

def create_job(db: Session, job_id: str, api_key: str, filename: str, storage_uri: str):
    job = Job(id=job_id, api_key=api_key, filename=filename, storage_uri=storage_uri, status="queued")
    db.add(job); db.commit(); db.refresh(job)
    return job

def update_job_result(db: Session, job_id: str, status: str, meta: dict, result: dict | None):
    job = db.get(Job, job_id)
    if not job:
        return None
    job.status = status
    job.meta_json = json.dumps(meta or {})
    job.result_json = json.dumps(result) if result is not None else "null"
    db.add(job); db.commit(); db.refresh(job)
    return job

def get_job(db: Session, job_id: str):
    return db.get(Job, job_id)

def inc_usage(db: Session, api_key: str, n: int = 1):
    m = month_now()
    row = db.query(Usage).filter(Usage.api_key == api_key, Usage.month == m).first()
    if not row:
        row = Usage(api_key=api_key, month=m, docs_parsed=0)
    row.docs_parsed += n
    db.add(row); db.commit(); db.refresh(row)
    return row

def get_usage(db: Session, api_key: str):
    m = month_now()
    row = db.query(Usage).filter(Usage.api_key == api_key, Usage.month == m).first()
    if not row:
        return {"month": m, "docs_parsed": 0}
    return {"month": row.month, "docs_parsed": row.docs_parsed}

def set_webhook(db: Session, api_key: str, url: str):
    row = db.query(Webhook).filter(Webhook.api_key == api_key).first()
    if not row:
        row = Webhook(api_key=api_key, url=url)
    else:
        row.url = url
    db.add(row); db.commit(); db.refresh(row)
    return row

def get_webhook(db: Session, api_key: str):
    return db.query(Webhook).filter(Webhook.api_key == api_key).first()
