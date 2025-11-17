import os, time, json
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, status, Form
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
# Load .env file, but don't override environment variables from docker-compose
load_dotenv(dotenv_path="/app/.env", override=False)

from fastapi import Header, File, UploadFile, HTTPException, status
from .security import verify_api_key, reload_api_keys
reload_api_keys()

from rq import Queue
from redis import Redis
from fastapi.responses import JSONResponse, HTMLResponse

from .security import verify_api_key
from .storage import save_file_to_s3, get_object_key
from .db import init_db, SessionLocal, get_job_by_id, create_job, create_batch, get_batch_by_id, get_jobs_by_batch, update_batch_stats, Job
from sqlalchemy.sql import func
from .schemas import JobResponse, UsageResponse, WebhookRegistration
from .tasks import enqueue_parse
from .exporters.tally_csv import invoice_to_tally_csv
from .exporters.tally_xml import invoice_to_tally_xml
from .exporters.registers import (
    export_json as export_parsed_json_str,
    sales_register_to_csv,
    purchase_register_to_csv,
    sales_register_to_zoho_json,
)
from .connectors.zoho_books import ZohoBooksClient, map_parsed_to_zoho_invoice

from .storage import save_file_to_s3, get_object_key, ensure_bucket

# ...
init_db()
ensure_bucket()  # <- create S3/MinIO bucket if missing (idempotent)


MAX_FILE_MB = int(os.getenv("MAX_FILE_MB","15"))

app = FastAPI(title="Doc Parser API PRO", version="0.2.0")

# CORS origins - configurable via environment variable
# Format: comma-separated list of origins, e.g., "http://localhost:3000,https://yourdomain.com"
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "x-api-key", "X-API-Key"],
)

# Redis connection - make it optional
redis_url = os.getenv("REDIS_URL", "")
try:
    if redis_url:
        redis = Redis.from_url(redis_url)
        q = Queue("docparser-queue", connection=redis)
    else:
        redis = None
        q = None
except Exception as e:
    print(f"Warning: Redis connection failed: {e}")
    redis = None
    q = None

init_db()

WEBHOOKS = {}

def _to_jsonable(x):
    if x is None:
        return None
    if isinstance(x, (dict, list, str, int, float, bool)):
        return x
    # some DBs store JSON as text/bytes — try to parse
    try:
        return json.loads(x)
    except Exception:
        try:
            return json.loads(bytes(x).decode("utf-8"))
        except Exception:
            return None

@app.get("/", response_class=HTMLResponse)
def root():
    """Simple styled landing/status page for the API."""
    year = time.strftime("%Y")
    # Get environment info
    env = os.getenv("ENV", "development").lower()
    env_label = "Production" if env == "production" else "Development"
    # Get frontend URL if configured
    frontend_url = os.getenv("FRONTEND_URL", os.getenv("CORS_ORIGINS", "").split(",")[0] if os.getenv("CORS_ORIGINS") else "")
    dashboard_text = f'visit the dashboard UI at <a href="{frontend_url}" style="color: #60a5fa; text-decoration: underline;">{frontend_url}</a>' if frontend_url else "dashboard UI available separately"
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Doc Parser API PRO</title>
      <style>
        :root {
          color-scheme: dark;
          --bg: #020617;
          --bg-elevated: #020617;
          --card: #020617;
          --card-border: #1e293b;
          --accent: #3b82f6;
          --accent-soft: rgba(59, 130, 246, 0.15);
          --text: #e5e7eb;
          --muted: #9ca3af;
          --danger: #f97373;
          --success: #22c55e;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          min-height: 100vh;
          font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
            sans-serif;
          background: radial-gradient(circle at top, #0b1120 0, #020617 45%, #000 100%);
          color: var(--text);
          -webkit-font-smoothing: antialiased;
        }
        .page {
          max-width: 1600px;
          margin: 0 auto;
          padding: 40px 32px 80px;
        }
        header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 14px 20px;
          border-radius: 999px;
          border: 1px solid rgba(148, 163, 184, 0.35);
          background: radial-gradient(circle at top left, rgba(59,130,246,0.25), transparent 55%),
                      rgba(15,23,42,0.9);
          backdrop-filter: blur(18px);
          box-shadow:
            0 18px 40px rgba(15, 23, 42, 0.9),
            0 0 0 1px rgba(15,23,42,1);
        }
        .brand {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .brand-mark {
          width: 32px;
          height: 32px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 11px;
          letter-spacing: 0.06em;
          font-weight: 600;
          color: #bfdbfe;
          background:
            conic-gradient(from 180deg at 50% 50%, #38bdf8 0deg, #6366f1 120deg, #a855f7 240deg, #38bdf8 360deg);
          position: relative;
        }
        .brand-mark::after {
          content: "";
          position: absolute;
          inset: 2px;
          border-radius: 10px;
          background: radial-gradient(circle at top, rgba(15,23,42,0.9), rgba(15,23,42,1));
        }
        .brand-mark span {
          position: relative;
          z-index: 1;
        }
        .brand-text-main {
          font-size: 14px;
          font-weight: 600;
          letter-spacing: -0.02em;
        }
        .brand-text-sub {
          font-size: 11px;
          color: var(--muted);
        }
        .tag {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 4px 10px;
          border-radius: 999px;
          font-size: 11px;
          background: rgba(15,23,42, 0.9);
          border: 1px solid rgba(148, 163, 184, 0.4);
          color: var(--muted);
        }
        .tag-dot {
          width: 7px;
          height: 7px;
          border-radius: 999px;
          background: var(--success);
          box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.25);
        }
        main {
          margin-top: 40px;
          display: grid;
          grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
          gap: 40px;
          margin-bottom: 40px;
        }
        @media (max-width: 1024px) {
          main {
            grid-template-columns: minmax(0, 1fr);
          }
        }
        .hero-heading {
          font-size: clamp(28px, 4vw, 42px);
          line-height: 1.2;
          letter-spacing: -0.03em;
          margin: 0 0 16px;
        }
        .hero-heading span {
          background-image: linear-gradient(to right, #60a5fa, #a855f7);
          -webkit-background-clip: text;
          color: transparent;
        }
        .hero-body {
          font-size: 14px;
          color: var(--muted);
          max-width: 600px;
          line-height: 1.6;
        }
        .pill-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 14px;
        }
        .pill {
          padding: 4px 10px;
          border-radius: 999px;
          border: 1px solid rgba(148, 163, 184, 0.3);
          font-size: 11px;
          color: var(--muted);
          background: rgba(15, 23, 42, 0.9);
        }
        .pill strong {
          color: var(--text);
          font-weight: 500;
        }
        .card {
          border-radius: 18px;
          border: 1px solid var(--card-border);
          background:
            radial-gradient(circle at top left, rgba(59,130,246,0.22), transparent 55%),
            radial-gradient(circle at bottom right, rgba(15,23,42,0.9), #020617);
          padding: 24px 28px 28px;
          box-shadow:
            0 22px 45px rgba(15, 23, 42, 0.9),
            0 0 0 1px rgba(15,23,42, 1);
        }
        .card h2 {
          margin: 0;
          font-size: 13px;
          font-weight: 600;
          letter-spacing: 0.02em;
          text-transform: uppercase;
          color: var(--muted);
        }
        .card-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px 20px;
          margin-top: 20px;
          font-size: 12px;
        }
        .card-col h3 {
          margin: 0 0 6px;
          font-size: 12px;
          font-weight: 500;
        }
        .card-col ul {
          margin: 0;
          padding-left: 16px;
          color: var(--muted);
        }
        .card-col li {
          margin: 2px 0;
        }
        .meta-row {
          display: grid;
          grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
          gap: 16px;
          margin-top: 24px;
          font-size: 11px;
        }
        .meta-row h4 {
          margin: 0 0 4px;
          font-size: 11px;
          font-weight: 500;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .meta-row p {
          margin: 0;
          color: var(--muted);
        }
        .meta-list {
          list-style: none;
          padding: 0;
          margin: 0;
          display: grid;
          gap: 4px;
        }
        .meta-list li {
          display: flex;
          justify-content: space-between;
          gap: 8px;
        }
        .meta-list span {
          color: var(--muted);
        }
        .meta-list strong {
          font-weight: 500;
          color: var(--text);
        }
        .panel {
          border-radius: 16px;
          border: 1px solid rgba(30, 64, 175, 0.8);
          background:
            radial-gradient(circle at top, rgba(37,99,235,0.25), transparent 55%),
            rgba(15,23,42, 0.96);
          padding: 24px 28px 28px;
          box-shadow:
            0 20px 45px rgba(15,23,42,0.95),
            0 0 0 1px rgba(15,23,42,1);
        }
        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          margin-bottom: 10px;
        }
        .panel-title {
          font-size: 13px;
          font-weight: 500;
        }
        .badge {
          font-size: 11px;
          padding: 3px 9px;
          border-radius: 999px;
          border: 1px solid rgba(96, 165, 250, 0.7);
          background: rgba(15, 23, 42, 0.95);
          color: var(--muted);
        }
        .status-pill {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 3px 10px;
          border-radius: 999px;
          font-size: 11px;
          background: rgba(21, 128, 61, 0.18);
          color: #bbf7d0;
          border: 1px solid rgba(34, 197, 94, 0.5);
        }
        .status-dot {
          width: 7px;
          height: 7px;
          border-radius: 999px;
          background: #22c55e;
        }
        code {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
          font-size: 11px;
          padding: 2px 6px;
          border-radius: 999px;
          background: rgba(15,23,42,0.9);
          border: 1px solid rgba(30,64,175,0.6);
          color: #bfdbfe;
        }
        .endpoints {
          margin-top: 10px;
          padding-top: 10px;
          border-top: 1px dotted rgba(30,64,175,0.7);
          font-size: 11px;
        }
        .endpoints-row {
          display: grid;
          gap: 6px;
        }
        .endpoint {
          display: flex;
          align-items: baseline;
          gap: 8px;
        }
        .endpoint-method {
          font-size: 10px;
          font-weight: 600;
          letter-spacing: 0.08em;
          padding: 2px 6px;
          border-radius: 999px;
          border: 1px solid rgba(96, 165, 250, 0.7);
          color: #bfdbfe;
          background: rgba(15,23,42,1);
        }
        .endpoint-path {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
          color: #e5e7eb;
        }
        .endpoint-desc {
          color: var(--muted);
        }
        footer {
          margin-top: 48px;
          font-size: 10px;
          color: #6b7280;
          display: flex;
          justify-content: space-between;
          gap: 8px;
          align-items: center;
        }
        footer span {
          opacity: 0.9;
        }
      </style>
    </head>
    <body>
      <div class="page">
        <header>
          <div class="brand">
            <div class="brand-mark"><span>DP</span></div>
            <div>
              <div class="brand-text-main">Doc Parser API PRO</div>
              <div class="brand-text-sub">AI document parsing for CAs &amp; Indian SMEs</div>
            </div>
          </div>
          <div class="tag">
            <span class="tag-dot"></span>
            <span>API online</span>
          </div>
        </header>

        <main>
          <section>
            <h1 class="hero-heading">
              Parse <span>bank statements, invoices &amp; GST PDFs</span> into clean JSON &amp; exports.
            </h1>
            <p class="hero-body">
              This is the backend for DocParser. Use your API key to upload financial and GST documents, then
              retrieve parsed JSON, CSV, Tally XML and reconciliation outputs that plug into Tally, Zoho and your
              own tools.
            </p>

            <div class="pill-row">
              <div class="pill"><strong>Version</strong> 0.2.0</div>
              <div class="pill"><strong>Max file size</strong> 15&nbsp;MB (default)</div>
              <div class="pill">Background jobs via Redis / RQ (if configured)</div>
            </div>

            <div class="card">
              <h2>What this API can do</h2>
              <div class="card-grid">
                <div class="card-col">
                  <h3>Understands your documents</h3>
                  <ul>
                    <li>Bank statements</li>
                    <li>GST invoices</li>
                    <li>GSTR‑1 &amp; GSTR‑3B returns</li>
                    <li>Purchase &amp; sales registers (PDF / CSV)</li>
                  </ul>
                </div>
                <div class="card-col">
                  <h3>Exports &amp; reconciliations</h3>
                  <ul>
                    <li>Tally XML for sales &amp; purchase vouchers</li>
                    <li>Standardized CSV for registers</li>
                    <li>Zoho Books‑ready JSON (sales invoices)</li>
                    <li>GSTR‑3B ITC &amp; GSTR‑1 / Sales reconciliation</li>
                  </ul>
                </div>
              </div>
              <div class="meta-row">
                <div>
                  <h4>How to start</h4>
                  <p>
                    Send a <code>POST /v1/parse</code> request with your document as
                    <code>file</code> (multipart) and your API key in the
                    <code>Authorization</code> or <code>X-API-Key</code> header.
                    We create a job and return a <code>job_id</code> you can poll.
                  </p>
                </div>
                <div>
                  <h4>Doc types</h4>
                  <ul class="meta-list">
                    <li><span>Automatic detection</span><strong>default</strong></li>
                    <li><span>Override</span><strong>doc_type=form field</strong></li>
                    <li><span>Examples</span><strong>bank_statement, sales_register</strong></li>
                  </ul>
                </div>
              </div>
            </div>
          </section>

          <section>
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">API status &amp; quick reference</div>
                  <div style="font-size: 11px; color: var(--muted); margin-top: 2px;">
                    Use this environment for development &amp; integration testing.
                  </div>
                </div>
                <div class="status-pill">
                  <span class="status-dot"></span>
                  <span>Healthy</span>
                </div>
              </div>

              <div style="display: grid; gap: 6px; font-size: 11px; margin-bottom: 8px;">
                <div>
                  <span style="color: var(--muted);">Current service</span>
                  <span style="margin-left: 6px; font-weight: 500; color: var(--text);">
                    Doc Parser API PRO
                  </span>
                </div>
                <div>
                  <span style="color: var(--muted);">Environment</span>
                  <span style="margin-left: 6px; font-weight: 500; color: var(--text);">
                    {env_label}
                  </span>
                </div>
              </div>

              <div class="endpoints">
                <div class="endpoints-row">
                  <div class="endpoint">
                    <span class="endpoint-method">POST</span>
                    <span class="endpoint-path">/v1/parse</span>
                  </div>
                  <div class="endpoint-desc">Upload a single document and create a parsing job.</div>

                  <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <span class="endpoint-path">/v1/jobs/&lt;job_id&gt;</span>
                  </div>
                  <div class="endpoint-desc">
                    Poll for parsed results, detected doc type, and reconciliations.
                  </div>

                  <div class="endpoint">
                    <span class="endpoint-method">POST</span>
                    <span class="endpoint-path">/v1/bulk-parse</span>
                  </div>
                  <div class="endpoint-desc">
                    Upload multiple documents as a batch and track them together.
                  </div>

                  <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <span class="endpoint-path">/v1/export/*</span>
                  </div>
                  <div class="endpoint-desc">
                    Download JSON, CSV, Tally XML or Zoho payloads for completed jobs.
                  </div>

                  <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <span class="endpoint-path">/health</span>
                  </div>
                  <div class="endpoint-desc">
                    JSON health/info endpoint (ok, service, version).
                  </div>
                </div>
              </div>
            </div>
          </section>
        </main>

        <footer>
          <span>&copy; {year} DocParser. All rights reserved.</span>
          <span>Backend service&nbsp;&mdash;&nbsp;{dashboard_text}.</span>
        </footer>
      </div>
    </body>
    </html>
    """.replace("{year}", year).replace("{env_label}", env_label).replace("{dashboard_text}", dashboard_text)
    return HTMLResponse(content=html)


@app.get("/health")
def health():
    """JSON health/info endpoint for monitoring and scripts."""
    return {"ok": True, "service": "Doc Parser API PRO", "version": "0.2.0"}

@app.get("/debug/api-keys")
def debug_api_keys():
    """Debug endpoint to check API keys configuration"""
    from .security import API_KEY_TENANTS, _load_key_map
    env_keys = os.getenv("API_KEYS", "")
    reloaded = _load_key_map()
    return {
        "env_API_KEYS": env_keys,
        "loaded_keys": list(API_KEY_TENANTS.keys()),
        "reloaded_keys": list(reloaded.keys()),
        "key_count": len(API_KEY_TENANTS)
    }

# app/main.py
@app.post("/v1/parse", response_model=JobResponse)
async def parse_endpoint(
    file: UploadFile = File(...),
    authorization: str | None = Header(None, alias="Authorization"),
    x_api_key: str | None = Header(None, alias="x-api-key"),
    doc_type: str | None = Form(None),
):
    try:
        api_key, tenant_id = verify_api_key(authorization, x_api_key)

        contents = await file.read()
        mb = len(contents) / (1024 * 1024)
        if mb > MAX_FILE_MB:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"File too large ({mb:.2f} MB). Max {MAX_FILE_MB} MB")

        object_key = get_object_key(file.filename)
        save_file_to_s3(object_key, contents)

        requested_doc_type = (doc_type or "").strip().lower() or None
        job_meta = {}
        if requested_doc_type:
            job_meta["requested_doc_type"] = requested_doc_type

        with SessionLocal() as dbs:
            job = create_job(dbs, object_key=object_key, filename=file.filename,
                             tenant_id=tenant_id, api_key=api_key, meta=job_meta or None)
        
        # Enqueue job if Redis is available, otherwise process synchronously
        if q:
            enqueue_parse(q, job.id)
        else:
            # If no Redis, process immediately (for development)
            from .worker import parse_job_task
            parse_job_task(job.id)
        
        return {
            "job_id": job.id,
            "status": "queued",
            "doc_type": job_meta.get("requested_doc_type") or "invoice",
            "result": None,
            "meta": job_meta,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"Internal error: {str(e)}\n{traceback.format_exc()}"
        print(f"ERROR in /v1/parse: {error_msg}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/v1/jobs")
async def list_jobs(
    limit: int = 10,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key")):
    """Get list of recent jobs for the authenticated tenant"""
    _, tenant_id = verify_api_key(authorization, x_api_key)

    with SessionLocal() as dbs:
        jobs = (
            dbs.query(Job)
            .filter(Job.tenant_id == tenant_id)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                "id": job.id,
                "job_id": job.id,
                "filename": job.filename or "Untitled",
                "doc_type": job.doc_type or "unknown",
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }
            for job in jobs
        ]

@app.get("/v1/jobs/{job_id}")
async def get_job(job_id: str,
                  authorization: str | None = Header(None),
                  x_api_key: str | None = Header(None, alias="x-api-key")):
    # reuse your API key check (supports Authorization and X-API-Key)
    _, _tenant_id = verify_api_key(authorization, x_api_key)

    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        result = _to_jsonable(getattr(job, "result", None))
        meta   = _to_jsonable(getattr(job, "meta", None)) or {}

        return {
            "job_id": job.id,
            "status": job.status,
            "doc_type": getattr(job, "doc_type", None),
            "filename": job.filename,
            "result": job.result,
            "meta": job.meta,
        }

@app.post("/v1/bulk-parse")
async def bulk_parse_endpoint(
    files: List[UploadFile] = File(...),
    client_id: Optional[str] = Form(None),
    batch_name: Optional[str] = Form(None),
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key"),
    doc_type: Optional[str] = Form(None),
):
    """Upload and parse multiple documents in a single batch"""
    api_key, tenant_id = verify_api_key(authorization, x_api_key)
    
    if len(files) > 100:  # Limit bulk uploads
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 files allowed per batch"
        )
    
    doc_type_override = (doc_type or "").strip().lower() or None
    base_meta: dict[str, str] = {}
    if doc_type_override:
        base_meta["requested_doc_type"] = doc_type_override

    # Create batch record
    with SessionLocal() as db:
        batch = create_batch(
            db, 
            tenant_id=tenant_id,
            client_id=client_id,
            batch_name=batch_name,
            total_files=len(files)
        )
        
        # Process files
        job_ids = []
        for file in files:
            try:
                contents = await file.read()
                mb = len(contents) / (1024 * 1024)
                
                if mb > MAX_FILE_MB:
                    update_batch_stats(db, batch.id, failed_files=1)
                    continue
                
                # Save file to S3
                object_key = get_object_key(file.filename)
                save_file_to_s3(object_key, contents)
                
                # Create job linked to batch
                job_meta = dict(base_meta)

                job = create_job(
                    db,
                    object_key=object_key,
                    filename=file.filename,
                    tenant_id=tenant_id,
                    api_key=api_key,
                    meta=job_meta or None,
                )
                
                # Update job with batch and client info
                job.batch_id = batch.id
                job.client_id = client_id
                db.commit()
                
                job_ids.append(job.id)
                
                # Enqueue for processing
                if q:
                    enqueue_parse(q, job.id)
                else:
                    from .worker import parse_job_task
                    parse_job_task(job.id)
                
            except Exception as e:
                update_batch_stats(db, batch.id, failed_files=1)
                continue
    
    return {
        "batch_id": batch.id,
        "total_files": len(files),
        "job_ids": job_ids,
        "status": "processing"
    }

@app.get("/v1/batches/{batch_id}")
async def get_batch_status(
    batch_id: str,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key"),
):
    """Get batch processing status and results"""
    api_key, tenant_id = verify_api_key(authorization, x_api_key)
    
    with SessionLocal() as db:
        batch = get_batch_by_id(db, batch_id)
        if not batch or batch.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Get all jobs in this batch
        jobs = get_jobs_by_batch(db, batch_id)
        
        # Calculate progress
        completed = sum(1 for job in jobs if job.status == "succeeded")
        failed = sum(1 for job in jobs if job.status == "failed")
        processing = sum(1 for job in jobs if job.status in ["queued", "processing"])
        
        # Update batch status
        if completed + failed == len(jobs):
            batch.status = "completed"
            batch.completed_at = func.now()
            db.commit()
        
        return {
            "batch_id": batch.id,
            "batch_name": batch.batch_name,
            "client_id": batch.client_id,
            "status": batch.status,
            "progress": {
                "total": len(jobs),
                "completed": completed,
                "failed": failed,
                "processing": processing
            },
            "jobs": [
                {
                    "job_id": job.id,
                    "filename": job.filename,
                    "status": job.status,
                    "doc_type": job.doc_type,
                    "result": job.result
                }
                for job in jobs
            ]
        }

@app.get("/v1/usage", response_model=UsageResponse)
def get_usage(authorization: str = Header(None)):
    api_key = verify_api_key(authorization)
    # TODO: aggregate from Jobs table by api_key and month
    return {"month": time.strftime("%Y-%m"), "docs_parsed": 0, "ocr_pages": 0}

@app.post("/v1/webhooks")
def register_webhook(body: WebhookRegistration, authorization: str = Header(None)):
    api_key = verify_api_key(authorization)
    WEBHOOKS[api_key] = body.url
    return {"ok": True, "url": body.url}

@app.get("/v1/export/tally-csv/{job_id}")
def export_tally_csv(job_id: str, authorization: str = Header(None)):
    verify_api_key(authorization)
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if not job or job.status != "succeeded" or not job.result:
            raise HTTPException(status_code=404, detail="job not found or not succeeded")
        csv_data = invoice_to_tally_csv(job.result)
        return JSONResponse(content={"filename": f"{job_id}.csv", "content": csv_data})


@app.get("/v1/export/tally-xml/{job_id}")
def export_tally_xml(job_id: str, authorization: str = Header(None)):
    verify_api_key(authorization)
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if not job or job.status != "succeeded" or not job.result:
            raise HTTPException(status_code=404, detail="job not found or not succeeded")
        xml = invoice_to_tally_xml(job.result)
        return JSONResponse(content={"filename": f"{job_id}.xml", "content": xml})


@app.post("/v1/push/zoho/{job_id}")
def push_to_zoho(job_id: str, body: dict, authorization: str = Header(None)):
    verify_api_key(authorization)
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if not job or job.status != "succeeded" or not job.result:
            raise HTTPException(status_code=404, detail="job not found or not succeeded")
        client = ZohoBooksClient(org_id=body.get("org_id"), access_token=body.get("access_token"))
        payload = map_parsed_to_zoho_invoice(job.result)
        code, resp = client.create_invoice(payload)
        return {"status_code": code, "response": resp, "payload": payload}


@app.get("/v1/export/json/{job_id}")
def export_parsed_json(job_id: str, authorization: str = Header(None)):
    verify_api_key(authorization)
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if not job or job.status != "succeeded" or not job.result:
            raise HTTPException(status_code=404, detail="job not found or not succeeded")
        json_body = export_parsed_json_str(job.result)
        return JSONResponse(
            content={"filename": f"{job_id}.json", "content": json_body}
        )


@app.get("/v1/export/sales-csv/{job_id}")
def export_sales_register_csv(job_id: str, authorization: str = Header(None)):
    verify_api_key(authorization)
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if (
            not job
            or job.status != "succeeded"
            or not job.result
            or job.doc_type != "sales_register"
        ):
            raise HTTPException(status_code=400, detail="Not a sales_register job")
        csv_data = sales_register_to_csv(job.result)
        return JSONResponse(
            content={"filename": f"sales_{job_id}.csv", "content": csv_data}
        )


@app.get("/v1/export/purchase-csv/{job_id}")
def export_purchase_register_csv(job_id: str, authorization: str = Header(None)):
    verify_api_key(authorization)
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if (
            not job
            or job.status != "succeeded"
            or not job.result
            or job.doc_type != "purchase_register"
        ):
            raise HTTPException(status_code=400, detail="Not a purchase_register job")
        csv_data = purchase_register_to_csv(job.result)
        return JSONResponse(
            content={"filename": f"purchase_{job_id}.csv", "content": csv_data}
        )


@app.get("/v1/export/sales-zoho/{job_id}")
def export_sales_register_zoho(job_id: str, authorization: str = Header(None)):
    verify_api_key(authorization)
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if (
            not job
            or job.status != "succeeded"
            or not job.result
            or job.doc_type != "sales_register"
        ):
            raise HTTPException(status_code=400, detail="Not a sales_register job")
        json_body = sales_register_to_zoho_json(job.result)
        return JSONResponse(
            content={"filename": f"zoho_invoices_{job_id}.json", "content": json_body}
        )
