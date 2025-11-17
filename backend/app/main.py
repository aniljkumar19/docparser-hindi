import os, uuid, time
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import redis
from rq import Queue

from .db import init_db, SessionLocal
from .models import Job, Webhook, Usage
from .schemas import JobResponse, WebhookRegistration, UsageResponse
from .security import verify_api_key
from .storage import put_bytes
from .virus import scan_bytes

MAX_FILE_MB = int(os.getenv("MAX_FILE_MB","15"))
REDIS_URL = os.getenv("REDIS_URL","redis://localhost:6379/0")

app = FastAPI(title="Doc Parser API PRO", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

def enqueue(job_id: str):
    r = redis.from_url(REDIS_URL)
    q = Queue("doc-jobs", connection=r)
    # Worker polls using custom loop, but enqueue stores job with args
    q.enqueue("app.workers.process_job", job_id)

@app.post("/v1/parse", response_model=JobResponse)
async def parse_endpoint(file: UploadFile = File(...), authorization: str = Header(None)):
    api_key = verify_api_key(authorization)
    contents = await file.read()
    mb = len(contents) / (1024*1024)
    if mb > MAX_FILE_MB:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File too large ({mb:.2f} MB). Max {MAX_FILE_MB} MB")
    if not scan_bytes(contents):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File flagged by antivirus")    
    # store file
    job_id = "job_" + uuid.uuid4().hex[:12]
    storage_key = f"uploads/{api_key}/{job_id}/{file.filename}"
    storage_key = put_bytes(storage_key, contents)

    db: Session = SessionLocal()
    job = Job(job_id=job_id, api_key=api_key, status="queued", storage_key=storage_key)
    db.add(job); db.commit()
    try:
        enqueue(job_id)
    finally:
        db.close()
    return JSONResponse({"job_id": job_id, "status": "queued", "doc_type":"invoice", "result": None, "meta": {}})

@app.get("/v1/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, authorization: str = Header(None)):
    verify_api_key(authorization)
    db: Session = SessionLocal()
    job = db.query(Job).filter_by(job_id=job_id).first()
    db.close()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return JSONResponse({
        "job_id": job.job_id,
        "status": job.status,
        "doc_type": job.doc_type,
        "result": job.result,
        "meta": job.meta or {}
    })

@app.get("/v1/usage", response_model=UsageResponse)
def get_usage(authorization: str = Header(None)):
    api_key = verify_api_key(authorization)
    db: Session = SessionLocal()
    month = time.strftime("%Y-%m")
    usage = db.query(Usage).filter_by(api_key=api_key, month=month).first()
    db.close()
    if not usage:
        return {"month": month, "docs_parsed": 0, "ocr_pages": 0}
    return {"month": usage.month, "docs_parsed": usage.docs, "ocr_pages": usage.ocr_pages}

@app.post("/v1/webhooks")
def register_webhook(body: WebhookRegistration, authorization: str = Header(None)):
    api_key = verify_api_key(authorization)
    db: Session = SessionLocal()
    wh = db.query(Webhook).filter_by(api_key=api_key).first()
    if wh:
        wh.url = body.url
    else:
        wh = Webhook(api_key=api_key, url=body.url)
        db.add(wh)
    db.commit(); db.close()
    return {"ok": True, "url": body.url}

@app.get("/")
def root():
    return {"ok": True, "service": "Doc Parser API PRO", "version": "0.2.0"}
