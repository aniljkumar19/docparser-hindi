import os, uuid
from fastapi import FastAPI, UploadFile, File, Header, BackgroundTasks, HTTPException, status, Response, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .security import verify_api_key
from .db import SessionLocal, init_db
from .repo import create_job, get_job, get_usage, set_webhook
from .storage import save_file
from .queueing import get_queue
from .tasks import process_job
from .schemas import JobResponse, UsageResponse, WebhookRegistration, INVOICE_V0_SCHEMA

MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "10"))
USE_QUEUE = bool(os.getenv("REDIS_URL"))

app = FastAPI(title="Doc Parser API (Pro)", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Auth dependency (verify & return the key string)
def auth_dep(authorization: str | None = Header(None)) -> str:
    ok, val = verify_api_key(authorization)
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=val)
    return val

# Serve the canonical JSON Schema for invoice.v0
@app.get("/v1/schema/invoice.v0")
def get_invoice_v0_schema(_: str = Depends(auth_dep)):
    return INVOICE_V0_SCHEMA

# simple registry (expand later with utility_bill.v0, bank_statement.v0, etc.)
SCHEMA_INDEX = {
    "invoice.v0": "/v1/schema/invoice.v0",
}

@app.get("/v1/schema")
def list_schemas(_: str = Depends(auth_dep)):
    return {"available": [{"name": k, "url": v} for k, v in SCHEMA_INDEX.items()]}

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

def db_dep():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def enqueue_or_background(background_tasks, job_id, api_key, filename, storage_uri):
    # TEMP: bypass Redis queue so jobs run immediately in the API process
    background_tasks.add_task(process_job, SessionLocal, job_id, api_key, filename, storage_uri)


# ⬇️ Changed: 202 status + Location header + doc_type="unknown" + return dict
from fastapi import Response, status

from fastapi import status  # keep this import

# /v1/parse
@app.post("/v1/parse", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def parse_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = Depends(auth_dep),   # <-- comes from dependency
     response: Response = None,
):
    contents = await file.read()
    mb = len(contents)/(1024*1024)
    if mb > MAX_FILE_MB:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"File too large ({mb:.2f} MB). Max {MAX_FILE_MB} MB")

    storage_uri = save_file(api_key, file.filename, contents)
    job_id = "job_" + uuid.uuid4().hex[:24]
    with SessionLocal() as db:
        create_job(db, job_id, api_key, file.filename, storage_uri)

    enqueue_or_background(background_tasks, job_id, api_key, file.filename, storage_uri)


    if response is not None:            # <-- add this line
        response.headers["Location"] = f"/v1/jobs/{job_id}"

    return {"job_id": job_id, "status": "queued", "doc_type": "unknown", "result": None, "meta": {}}





#
@app.get("/v1/jobs/{job_id}", response_model=JobResponse)
def get_job_endpoint(job_id: str, _: str = Depends(auth_dep)):
    with SessionLocal() as db:
        row = get_job(db, job_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        import json
        result = json.loads(row.result_json) if row.result_json and row.result_json != "null" else None
        doc_type = result.get("doc_type") if isinstance(result, dict) else "unknown"
        meta = json.loads(row.meta_json) if row.meta_json else {}
        return {
            "job_id": row.id,
            "status": row.status,
            "doc_type": doc_type or "unknown",
            "result": result,
            "meta": meta,
        }

# /v1/usage — needs the key value
@app.get("/v1/usage", response_model=UsageResponse)
def usage_endpoint(api_key: str = Depends(auth_dep)):
    with SessionLocal() as db:
        u = get_usage(db, api_key)
        return {"month": u["month"], "docs_parsed": u["docs_parsed"]}


# /v1/webhooks — needs the key value
@app.post("/v1/webhooks")
def register_webhook(body: WebhookRegistration, api_key: str = Depends(auth_dep)):
    with SessionLocal() as db:
        set_webhook(db, api_key, body.url)
    return {"ok": True, "url": body.url}

@app.get("/")
def root():
    return {"ok": True, "service": "Doc Parser API (Pro)", "version": "0.2.0"}

