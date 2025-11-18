import os, time, json
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, status, Form
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
# Load .env file, but don't override environment variables from docker-compose
load_dotenv(dotenv_path="/app/.env", override=False)

from fastapi import Header, File, UploadFile, HTTPException, status
from .security import verify_api_key, reload_api_keys, API_KEY_TENANTS
reload_api_keys()

# Log API keys status on startup
import logging
logging.info("=== API Keys Status ===")
logging.info(f"Loaded {len(API_KEY_TENANTS)} API keys: {list(API_KEY_TENANTS.keys())}")
logging.info(f"dev_123 available: {'dev_123' in API_KEY_TENANTS}")
api_keys_env = os.getenv("API_KEYS", "")
logging.info(f"API_KEYS env var: '{api_keys_env}' (empty={not api_keys_env})")
logging.info("======================")

# Import new API key system (optional - controlled by env var)
USE_API_KEY_MIDDLEWARE = os.getenv("USE_API_KEY_MIDDLEWARE", "false").lower() == "true"
if USE_API_KEY_MIDDLEWARE:
    from .middleware.auth import ApiKeyAuthMiddleware

from rq import Queue
from redis import Redis
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .security import verify_api_key
from .storage import save_file_to_s3, get_object_key
from .db import init_db, SessionLocal, get_job_by_id, create_job, create_batch, get_batch_by_id, get_jobs_by_batch, update_batch_stats, Job
from sqlalchemy.sql import func, text
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
from .exporters.reconciliation import (
    export_missing_invoices_csv,
    export_value_mismatches_csv,
    export_itc_mismatch_summary_csv,
)
from .connectors.zoho_books import ZohoBooksClient, map_parsed_to_zoho_invoice

from .storage import save_file_to_s3, get_object_key, ensure_bucket

# Import API key management endpoints
from .api_keys import router as api_keys_router

# Import admin API key endpoints
from .routers.admin_api_keys import router as admin_api_keys_router

# ...
# Initialize database (with error handling)
try:
    init_db()
except Exception as e:
    import logging
    logging.error(f"Database initialization failed: {e}")
    # Don't crash on startup - let it fail on first request if needed

# Log environment variable status on startup
import logging
logging.info("=== Environment Variables Check ===")
admin_token = os.getenv("ADMIN_TOKEN")
logging.info(f"ADMIN_TOKEN configured: {bool(admin_token)}")
logging.info(f"ADMIN_TOKEN length: {len(admin_token) if admin_token else 0}")
# List all env vars that contain 'ADMIN' (case insensitive)
admin_vars = [k for k in os.environ.keys() if 'ADMIN' in k.upper()]
logging.info(f"Environment variables with 'ADMIN': {admin_vars}")
logging.info("===================================")
# Initialize S3/MinIO bucket (with error handling)
try:
    ensure_bucket()
except Exception as e:
    import logging
    logging.warning(f"S3/MinIO initialization failed: {e}")
    logging.warning("File uploads may not work until S3 is configured")


MAX_FILE_MB = int(os.getenv("MAX_FILE_MB","15"))

app = FastAPI(title="Doc Parser API PRO", version="0.2.0")

# Include API key management router
app.include_router(api_keys_router)

# Include admin API key router (protected by ADMIN_TOKEN)
app.include_router(admin_api_keys_router)

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

# Add API key authentication middleware (if enabled)
# When enabled, this handles auth + rate limiting automatically
# When disabled, endpoints use the legacy verify_api_key() function
if USE_API_KEY_MIDDLEWARE:
    app.add_middleware(ApiKeyAuthMiddleware)

# Redis connection - make it optional
# Only connect if REDIS_URL is explicitly set AND not pointing to localhost (which won't work in Railway)
redis_url = os.getenv("REDIS_URL", "").strip()
redis = None
q = None

if redis_url:
    # Skip if it's a localhost URL (won't work in Railway without a Redis service)
    if redis_url.startswith("redis://localhost") or redis_url.startswith("redis://127.0.0.1"):
        print(f"Warning: REDIS_URL points to localhost ({redis_url}), skipping Redis connection. Jobs will process synchronously.")
    else:
        try:
            redis = Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
            # Test connection
            redis.ping()
            q = Queue("docparser-queue", connection=redis)
            print(f"✅ Redis connected: {redis_url}")
        except Exception as e:
            print(f"⚠️  Warning: Redis connection failed ({e}). Jobs will process synchronously.")
            redis = None
            q = None
else:
    print("ℹ️  REDIS_URL not set. Jobs will process synchronously (no background queue).")

# init_db() already called above with error handling

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
    # Check if we're on Railway (Railway sets RAILWAY_ENVIRONMENT or RAILWAY_SERVICE_NAME)
    is_railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_SERVICE_NAME"))
    if env == "production":
        env_label = "Production"
        env_description = "Production environment for live usage."
    elif is_railway:
        env_label = "Cloud beta (Railway)"
        env_description = "Use this environment for beta testing with real documents (review outputs before filing)."
    else:
        env_label = "Development"
        env_description = "Use this environment for development & integration testing."
    
    # Get frontend URL if configured - construct dashboard URL
    base_url = os.getenv("FRONTEND_URL") or os.getenv("RAILWAY_PUBLIC_DOMAIN") or (os.getenv("CORS_ORIGINS", "").split(",")[0] if os.getenv("CORS_ORIGINS") else "")
    if base_url:
        # Construct dashboard URL (remove protocol if present, add if needed)
        if base_url.startswith("http://") or base_url.startswith("https://"):
            dashboard_url = f"{base_url}/dashboard"
        else:
            dashboard_url = f"https://{base_url}/dashboard"
        dashboard_text = f'visit the dashboard UI at <a href="{dashboard_url}" style="color: #60a5fa; text-decoration: underline;">{dashboard_url}</a>'
    else:
        dashboard_text = "dashboard UI available separately"
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
                    <code>file</code> (multipart) and your API key in the header.
                    Include your API key in either:
                  </p>
                  <ul style="margin: 8px 0; padding-left: 20px; color: var(--muted); font-size: 11px;">
                    <li><code>Authorization: Bearer &lt;YOUR_API_KEY&gt;</code></li>
                    <li><code>X-API-Key: &lt;YOUR_API_KEY&gt;</code></li>
                  </ul>
                  <p style="margin-top: 8px; font-size: 11px; color: var(--muted);">
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
                    {env_description}
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
    """.replace("{year}", year).replace("{env_label}", env_label).replace("{env_description}", env_description).replace("{dashboard_text}", dashboard_text)
    return HTMLResponse(content=html)


# Mount static files for dashboard (if they exist)
dashboard_static_path = Path("/app/dashboard/out")
if dashboard_static_path.exists():
    # Next.js static export creates: out/dashboard/index.html for /dashboard route
    # Serve the dashboard page explicitly
    @app.get("/dashboard")
    @app.get("/dashboard/")
    async def serve_dashboard():
        # Try multiple possible paths for Next.js static export
        possible_paths = [
            dashboard_static_path / "dashboard" / "index.html",  # /dashboard route
            dashboard_static_path / "index.html",  # Root fallback
        ]
        
        for dashboard_index in possible_paths:
            if dashboard_index.exists():
                return FileResponse(str(dashboard_index))
        
        # If not found, return helpful error
        return HTMLResponse(
            content=f"""
            <h1>Dashboard not found</h1>
            <p>Dashboard files not found. Checked:</p>
            <ul>
                <li>{dashboard_static_path / "dashboard" / "index.html"}</li>
                <li>{dashboard_static_path / "index.html"}</li>
            </ul>
            <p>Dashboard path exists: {dashboard_static_path.exists()}</p>
            """,
            status_code=404
        )
    
    # Serve static assets (JS, CSS, etc.) from the _next directory
    next_static_path = dashboard_static_path / "_next"
    if next_static_path.exists():
        app.mount("/_next", StaticFiles(directory=str(next_static_path)), name="dashboard-assets")
    
    # Serve other static assets (fonts, images, etc.) that might be in the out directory
    # But NOT at /dashboard to avoid conflict with our route handler above
    # These will be served from their relative paths in the HTML


@app.get("/health")
def health():
    """JSON health/info endpoint for monitoring and scripts."""
    return {"ok": True, "service": "Doc Parser API PRO", "version": "0.2.0"}

@app.get("/debug/dashboard")
def debug_dashboard():
    """Debug endpoint to check dashboard file structure."""
    dashboard_static_path = Path("/app/dashboard/out")
    result = {
        "dashboard_path_exists": dashboard_static_path.exists(),
        "dashboard_path": str(dashboard_static_path),
        "files": {}
    }
    
    if dashboard_static_path.exists():
        # Check for dashboard/index.html
        dashboard_index = dashboard_static_path / "dashboard" / "index.html"
        result["files"]["dashboard/index.html"] = dashboard_index.exists()
        
        # Check for root index.html
        root_index = dashboard_static_path / "index.html"
        result["files"]["index.html"] = root_index.exists()
        
        # List top-level files/dirs
        try:
            result["top_level"] = [f.name for f in dashboard_static_path.iterdir() if f.is_file()][:10]
            result["top_level_dirs"] = [f.name for f in dashboard_static_path.iterdir() if f.is_dir()][:10]
        except Exception as e:
            result["error"] = str(e)
    
    return result

@app.get("/debug/job/{job_id}")
def debug_job(job_id: str, authorization: str | None = Header(None), x_api_key: str | None = Header(None, alias="x-api-key")):
    """Debug endpoint to check job result format."""
    try:
        verify_api_key(authorization, x_api_key)
    except:
        pass  # Allow without auth for debugging
    
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if not job:
            return {"error": "Job not found", "job_id": job_id}
        
        result_raw = job.result
        result_parsed = _to_jsonable(result_raw)
        
        return {
            "job_id": job_id,
            "status": job.status,
            "doc_type": job.doc_type,
            "result_type": str(type(result_raw)),
            "result_parsed_type": str(type(result_parsed)),
            "result_is_dict": isinstance(result_parsed, dict),
            "result_is_list": isinstance(result_parsed, list),
            "result_is_string": isinstance(result_parsed, str),
            "result_preview": str(result_parsed)[:200] if result_parsed else None,
        }

@app.get("/debug/api-keys")
def debug_api_keys():
    """Debug endpoint to check API keys configuration"""
    from .security import API_KEY_TENANTS, _load_key_map, hash_api_key
    from .db import SessionLocal, ApiKey, DB_URL
    env_keys = os.getenv("API_KEYS", "")
    reloaded = _load_key_map()
    admin_token = os.getenv("ADMIN_TOKEN", "")
    
    # Check database keys
    db_keys = []
    db_connection_info = {}
    try:
        with SessionLocal() as db:
            # Test database connection
            db.execute(text("SELECT 1"))
            
            # Get all keys
            db_key_objs = db.query(ApiKey).all()
            for k in db_key_objs:
                db_keys.append({
                    "id": k.id,
                    "name": k.name,
                    "tenant_id": k.tenant_id,
                    "is_active": k.is_active,
                    "created_at": str(k.created_at) if k.created_at else None,
                })
            
            # Get table info
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            tables = inspector.get_table_names(schema="docparser" if "postgresql" in DB_URL.lower() else None)
            db_connection_info = {
                "connected": True,
                "database_url_preview": DB_URL[:50] + "..." if len(DB_URL) > 50 else DB_URL,
                "tables": tables,
                "api_keys_table_exists": "api_keys" in tables or any("api_key" in t.lower() for t in tables),
            }
    except Exception as e:
        db_connection_info = {
            "connected": False,
            "error": str(e),
            "database_url_preview": DB_URL[:50] + "..." if len(DB_URL) > 50 else DB_URL,
        }
    
    # Test hash for dev_123
    dev_123_hash = hash_api_key("dev_123")
    dev_123_in_db = False
    try:
        with SessionLocal() as db:
            dev_123_obj = db.query(ApiKey).filter(ApiKey.key_hash == dev_123_hash).first()
            dev_123_in_db = dev_123_obj is not None
    except Exception as e:
        pass
    
    return {
        "env_API_KEYS": env_keys,
        "loaded_keys": list(API_KEY_TENANTS.keys()),
        "reloaded_keys": list(reloaded.keys()),
        "key_count": len(API_KEY_TENANTS),
        "ADMIN_TOKEN_configured": bool(admin_token),
        "database_keys": db_keys,
        "database_key_count": len(db_keys),
        "database_connection": db_connection_info,
        "dev_123_in_env": "dev_123" in API_KEY_TENANTS,
        "dev_123_in_database": dev_123_in_db,
        "ADMIN_TOKEN_length": len(admin_token) if admin_token else 0,
        "ADMIN_TOKEN_preview": admin_token[:4] + "..." if admin_token and len(admin_token) > 4 else "not set"
    }

@app.get("/debug/recent-api-keys")
def debug_recent_api_keys(limit: int = 5):
    """Check the most recently created API keys in the database"""
    from .db import SessionLocal, ApiKey
    import logging
    
    try:
        with SessionLocal() as db:
            # Get most recent keys ordered by created_at
            recent_keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).limit(limit).all()
            
            keys_info = []
            for k in recent_keys:
                keys_info.append({
                    "id": k.id,
                    "name": k.name,
                    "tenant_id": k.tenant_id,
                    "is_active": k.is_active,
                    "created_at": str(k.created_at) if k.created_at else None,
                    "created_by": k.created_by,
                    "last_used_at": str(k.last_used_at) if k.last_used_at else "Never",
                    "hash_preview": k.key_hash[:16] + "..." if k.key_hash else None,
                })
            
            logging.info(f"Found {len(recent_keys)} recent API keys in database")
            
            return {
                "success": True,
                "total_found": len(recent_keys),
                "recent_keys": keys_info,
                "message": f"Found {len(recent_keys)} API key(s) in database" if recent_keys else "No API keys found in database"
            }
    except Exception as e:
        import traceback
        logging.error(f"Error checking recent API keys: {e}")
        logging.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.post("/debug/test-api-key")
def test_api_key(authorization: str | None = Header(None), x_api_key: str | None = Header(None, alias="x-api-key")):
    """Test endpoint to verify API key extraction and validation"""
    import logging
    from .security import _extract_key, hash_api_key, API_KEY_TENANTS
    from .db import SessionLocal, ApiKey
    
    try:
        key = _extract_key(authorization, x_api_key)
        key_preview = key[:8] + "..." if len(key) > 8 else key
        key_hash = hash_api_key(key)
        
        # Check database - get all keys for comparison
        db_match = None
        all_db_keys = []
        with SessionLocal() as db:
            # Get the matching key
            api_key_obj = db.query(ApiKey).filter(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == "active"
            ).first()
            if api_key_obj:
                db_match = {
                    "id": api_key_obj.id,
                    "name": api_key_obj.name,
                    "tenant_id": api_key_obj.tenant_id,
                    "is_active": api_key_obj.is_active,
                }
            
            # Get all active keys for comparison
            all_keys = db.query(ApiKey).filter(ApiKey.is_active == "active").all()
            for k in all_keys:
                all_db_keys.append({
                    "id": k.id,
                    "name": k.name,
                    "hash_preview": k.key_hash[:16] + "...",
                    "tenant_id": k.tenant_id,
                })
        
        # Check env vars
        env_match = API_KEY_TENANTS.get(key)
        
        return {
            "key_received": key_preview,
            "key_length": len(key),
            "key_starts_with": key[:10] if len(key) >= 10 else key,
            "key_hash": key_hash[:16] + "...",
            "database_match": db_match,
            "all_database_keys": all_db_keys,
            "env_var_match": env_match,
            "authorization_header": authorization[:30] + "..." if authorization and len(authorization) > 30 else authorization,
            "x_api_key_header": x_api_key[:20] + "..." if x_api_key and len(x_api_key) > 20 else x_api_key,
            "valid": bool(db_match or env_match),
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "authorization_header": authorization[:30] + "..." if authorization and len(authorization) > 30 else authorization,
            "x_api_key_header": x_api_key[:20] + "..." if x_api_key and len(x_api_key) > 20 else x_api_key,
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
        # For development: always include jobs with empty tenant_id
        # This helps when jobs were created before tenant_id was properly set
        from sqlalchemy import or_
        query = dbs.query(Job)
        
        if tenant_id:
            # Show jobs matching tenant_id OR jobs with empty tenant_id (for development)
            query = query.filter(or_(Job.tenant_id == tenant_id, Job.tenant_id == "", Job.tenant_id.is_(None)))
        else:
            # If no tenant_id, show only jobs with empty tenant_id
            query = query.filter(or_(Job.tenant_id == "", Job.tenant_id.is_(None)))
        
        jobs = (
            query
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
        try:
            job = get_job_by_id(dbs, job_id)
        except Exception as e:
            import logging
            logging.error(f"Error fetching job {job_id}: {e}")
            raise HTTPException(status_code=404, detail=f"Job not found: {str(e)}")
        
        if not job:
            # Log for debugging
            import logging
            logging.warning(f"Job {job_id} not found in database (tenant_id={_tenant_id})")
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
def export_tally_csv(job_id: str, authorization: str = Header(None), x_api_key: str = Header(None, alias="x-api-key")):
    try:
        verify_api_key(authorization, x_api_key)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    
    try:
        with SessionLocal() as dbs:
            job = get_job_by_id(dbs, job_id)
            if not job or job.status != "succeeded" or not job.result:
                raise HTTPException(status_code=404, detail="job not found or not succeeded")
            
            result = job.result
            if isinstance(result, str):
                import json
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=500, detail="Invalid JSON in job result")
            
            if not isinstance(result, dict):
                raise HTTPException(status_code=500, detail=f"Expected dict result, got {type(result).__name__}")
            
            # Check if this is a register (has entries array)
            if "entries" in result:
                # Register document - process all entries
                import csv
                from io import StringIO
                buf = StringIO()
                w = csv.writer(buf)
                w.writerow(["Date","Invoice Number","Party Name","GSTIN","Item","Qty","Rate","Amount","CGST","SGST","IGST","Total"])
                
                for entry in result.get("entries", []):
                    # Convert register entry to invoice-like structure for Tally CSV
                    invoice_data = {
                        "invoice_number": entry.get("invoice_number"),
                        "date": entry.get("invoice_date"),
                        "buyer": {
                            "name": entry.get("customer_name") or entry.get("supplier_name") or "",
                            "gstin": entry.get("customer_gstin") or entry.get("supplier_gstin") or ""
                        },
                        "taxes": [
                            {"type": "CGST", "amount": entry.get("cgst", 0)},
                            {"type": "SGST", "amount": entry.get("sgst", 0)},
                            {"type": "IGST", "amount": entry.get("igst", 0)}
                        ],
                        "total": entry.get("total_value", 0),
                        "line_items": [{
                            "desc": "Invoice Item",
                            "qty": 1,
                            "unit_price": entry.get("taxable_value", 0),
                            "amount": entry.get("taxable_value", 0)
                        }]
                    }
                    # Generate CSV for this invoice (without header)
                    csv_row = invoice_to_tally_csv(invoice_data)
                    # Skip the header row (first line) and write data rows
                    lines = csv_row.strip().split('\n')
                    if len(lines) > 1:
                        # Write all lines except the first (header)
                        for line in lines[1:]:
                            buf.write(line + '\n')
                    elif len(lines) == 1 and lines[0].strip():
                        # If only one line (no header), write it
                        buf.write(lines[0] + '\n')
                
                csv_data = buf.getvalue()
            else:
                # Single invoice
                csv_data = invoice_to_tally_csv(result)
            
            return JSONResponse(content={"filename": f"{job_id}.csv", "content": csv_data})
    except HTTPException:
        raise
    except Exception as e:
        import logging
        import traceback
        logging.error(f"Error exporting Tally CSV: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Tally CSV: {str(e)}")


@app.get("/v1/export/tally-xml/{job_id}")
def export_tally_xml(job_id: str, authorization: str = Header(None), x_api_key: str = Header(None, alias="x-api-key")):
    try:
        verify_api_key(authorization, x_api_key)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    
    try:
        with SessionLocal() as dbs:
            job = get_job_by_id(dbs, job_id)
            if not job or job.status != "succeeded" or not job.result:
                raise HTTPException(status_code=404, detail="job not found or not succeeded")
            
            result = job.result
            if isinstance(result, str):
                import json
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=500, detail="Invalid JSON in job result")
            
            if not isinstance(result, dict):
                raise HTTPException(status_code=500, detail=f"Expected dict result, got {type(result).__name__}")
            
            # Check if this is a register (has entries array)
            if "entries" in result:
                # Register document - determine voucher type from job doc_type
                # Get doc_type from job if available, otherwise infer from register structure
                doc_type = job.doc_type if hasattr(job, 'doc_type') else None
                if not doc_type:
                    # Infer from register structure - purchase has supplier_name, sales has customer_name
                    first_entry = result.get("entries", [{}])[0] if result.get("entries") else {}
                    if "supplier_name" in first_entry:
                        doc_type = "purchase_register"
                    elif "customer_name" in first_entry:
                        doc_type = "sales_register"
                
                voucher_type = "Purchase" if doc_type == "purchase_register" else "Sales"
                
                # Build XML with one TALLYMESSAGE per voucher
                xml_parts = []
                xml_parts.append("""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
      </REQUESTDESC>
      <REQUESTDATA>""")
                
                for entry in result.get("entries", []):
                    # Convert register entry to invoice-like structure for Tally XML
                    invoice_data = {
                        "invoice_number": entry.get("invoice_number"),
                        "date": entry.get("invoice_date"),
                        "buyer": {
                            "name": entry.get("customer_name") or entry.get("supplier_name") or "",
                            "gstin": entry.get("customer_gstin") or entry.get("supplier_gstin") or ""
                        },
                        "subtotal": entry.get("taxable_value", 0),
                        "total": entry.get("total_value", 0),
                        "cgst": entry.get("cgst", 0),
                        "sgst": entry.get("sgst", 0),
                        "igst": entry.get("igst", 0),
                        "taxes": [
                            {"type": "CGST", "amount": entry.get("cgst", 0)},
                            {"type": "SGST", "amount": entry.get("sgst", 0)},
                            {"type": "IGST", "amount": entry.get("igst", 0)}
                        ],
                        "line_items": [{
                            "desc": "Invoice Item",
                            "qty": 1,
                            "unit_price": entry.get("taxable_value", 0),
                            "amount": entry.get("taxable_value", 0)
                        }]
                    }
                    # Generate XML for this voucher with correct voucher type
                    single_xml = invoice_to_tally_xml(invoice_data, voucher_type=voucher_type)
                    # Extract the TALLYMESSAGE block (one per voucher)
                    if "<TALLYMESSAGE" in single_xml:
                        msg_start = single_xml.find("<TALLYMESSAGE")
                        msg_end = single_xml.find("</TALLYMESSAGE>") + len("</TALLYMESSAGE>")
                        if msg_start >= 0 and msg_end > msg_start:
                            tally_message = single_xml[msg_start:msg_end]
                            xml_parts.append("        " + tally_message)
                
                xml_parts.append("""      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>""")
                xml = "\n".join(xml_parts)
            else:
                # Single invoice
                xml = invoice_to_tally_xml(result)
            
            # Validate XML syntax before returning
            try:
                import xml.etree.ElementTree as ET
                ET.fromstring(xml)
                logging.info("✅ XML syntax validation passed")
            except ET.ParseError as e:
                logging.error(f"❌ XML syntax error: {e}")
                logging.error(f"   XML preview (first 500 chars): {xml[:500]}")
                # Still return XML but log the error
            except Exception as e:
                logging.warning(f"⚠️  Could not validate XML syntax: {e}")
            
            return JSONResponse(content={"filename": f"{job_id}.xml", "content": xml})
    except HTTPException:
        raise
    except Exception as e:
        import logging
        import traceback
        logging.error(f"Error exporting Tally XML: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Tally XML: {str(e)}")


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
def export_parsed_json(
    job_id: str, 
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key")
):
    """Export parsed JSON for a completed job."""
    try:
        verify_api_key(authorization, x_api_key)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status != "succeeded":
            raise HTTPException(status_code=400, detail=f"Job not completed (status: {job.status})")
        if not job.result:
            raise HTTPException(status_code=404, detail="Job has no result data")
        
        # Ensure result is a dict (might be stored as JSON string)
        result = _to_jsonable(job.result)
        if result is None:
            raise HTTPException(status_code=404, detail="Job result is empty")
        
        # If result is a string, try to parse it as JSON
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail="Job result is not valid JSON")
        
        if not isinstance(result, dict):
            import logging
            logging.error(f"Job {job_id} result is not a dict: {type(result)}, value: {str(result)[:100]}")
            # Try to wrap it in a dict if it's a list or other type
            if isinstance(result, (list, str, int, float)):
                result = {"data": result}
            else:
                raise HTTPException(status_code=500, detail=f"Invalid job result format: {type(result)}")
        
        try:
            json_body = export_parsed_json_str(result)
            return JSONResponse(
                content={"filename": f"{job_id}.json", "content": json_body}
            )
        except Exception as e:
            import logging
            import traceback
            logging.error(f"Export JSON error for job {job_id}: {e}")
            logging.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Failed to export JSON: {str(e)}")


@app.get("/v1/export/sales-csv/{job_id}")
def export_sales_register_csv(job_id: str, authorization: str = Header(None), x_api_key: str = Header(None, alias="x-api-key")):
    verify_api_key(authorization, x_api_key)
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
def export_purchase_register_csv(job_id: str, authorization: str = Header(None), x_api_key: str = Header(None, alias="x-api-key")):
    verify_api_key(authorization, x_api_key)
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
def export_sales_register_zoho(job_id: str, authorization: str = Header(None), x_api_key: str = Header(None, alias="x-api-key")):
    verify_api_key(authorization, x_api_key)
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


@app.get("/v1/export/reconciliation/missing-invoices/{job_id}")
def export_missing_invoices(
    job_id: str,
    type: str = "gstr1",  # "gstr1" or "sales_register"
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key")
):
    """Export missing invoices CSV for reconciliation."""
    verify_api_key(authorization, x_api_key)
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if not job or job.status != "succeeded" or not job.meta:
            raise HTTPException(status_code=400, detail="Job not found or not completed")
        
        reconciliations = job.meta.get("reconciliations", {})
        sales_recon = reconciliations.get("sales_vs_gstr1", {})
        
        if not sales_recon:
            raise HTTPException(status_code=404, detail="No sales vs GSTR-1 reconciliation found")
        
        missing_invoices = []
        filename_prefix = ""
        
        if type == "gstr1":
            missing_invoices = sales_recon.get("missing_in_gstr1", [])
            filename_prefix = "missing_in_gstr1"
        elif type == "sales_register":
            missing_invoices = sales_recon.get("missing_in_sales_register", [])
            filename_prefix = "missing_in_sales_register"
        else:
            raise HTTPException(status_code=400, detail="Invalid type. Use 'gstr1' or 'sales_register'")
        
        if not missing_invoices:
            raise HTTPException(status_code=404, detail=f"No missing invoices found for type: {type}")
        
        csv_data = export_missing_invoices_csv(missing_invoices, source=type)
        return JSONResponse(
            content={"filename": f"{filename_prefix}_{job_id}.csv", "content": csv_data}
        )


@app.get("/v1/export/reconciliation/value-mismatches/{job_id}")
def export_value_mismatches(
    job_id: str,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key")
):
    """Export value mismatches CSV for sales register vs GSTR-1 reconciliation."""
    verify_api_key(authorization, x_api_key)
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if not job or job.status != "succeeded" or not job.meta:
            raise HTTPException(status_code=400, detail="Job not found or not completed")
        
        reconciliations = job.meta.get("reconciliations", {})
        sales_recon = reconciliations.get("sales_vs_gstr1", {})
        
        if not sales_recon:
            raise HTTPException(status_code=404, detail="No sales vs GSTR-1 reconciliation found")
        
        value_mismatches = sales_recon.get("value_mismatches", [])
        if not value_mismatches:
            raise HTTPException(status_code=404, detail="No value mismatches found")
        
        csv_data = export_value_mismatches_csv(value_mismatches)
        return JSONResponse(
            content={"filename": f"value_mismatches_{job_id}.csv", "content": csv_data}
        )


@app.get("/v1/export/reconciliation/itc-summary/{job_id}")
def export_itc_summary(
    job_id: str,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key")
):
    """Export ITC mismatch summary CSV for purchase register vs GSTR-3B reconciliation."""
    verify_api_key(authorization, x_api_key)
    with SessionLocal() as dbs:
        job = get_job_by_id(dbs, job_id)
        if not job or job.status != "succeeded" or not job.meta:
            raise HTTPException(status_code=400, detail="Job not found or not completed")
        
        reconciliations = job.meta.get("reconciliations", {})
        itc_recon = reconciliations.get("purchase_vs_gstr3b_itc", {})
        
        if not itc_recon:
            raise HTTPException(status_code=404, detail="No purchase vs GSTR-3B ITC reconciliation found")
        
        csv_data = export_itc_mismatch_summary_csv(itc_recon)
        return JSONResponse(
            content={"filename": f"itc_summary_{job_id}.csv", "content": csv_data}
        )


# Sample documents endpoints
@app.get("/v1/samples")
def list_sample_documents():
    """List available sample documents for testing."""
    samples_dir = Path("/app/samples") if Path("/app/samples").exists() else Path(__file__).parent.parent.parent / "samples"
    
    samples = []
    sample_files = {
        "GSTR1.pdf": {"name": "GSTR-1 Return", "type": "gstr1", "description": "Sample GSTR-1 return for testing reconciliation"},
        "GSTR-3B.pdf": {"name": "GSTR-3B Return", "type": "gstr3b", "description": "Sample GSTR-3B return for ITC reconciliation"},
        "sales_register.csv": {"name": "Sales Register", "type": "sales_register", "description": "Sample sales register CSV"},
        "purchase_register_complex.csv": {"name": "Purchase Register", "type": "purchase_register", "description": "Sample purchase register CSV"},
    }
    
    # Add a sample invoice if available
    invoice_files = ["sample_invoice.txt", "GSTN.pdf"]
    for inv_file in invoice_files:
        if (samples_dir / inv_file).exists():
            sample_files[inv_file] = {
                "name": "Sample Invoice",
                "type": "invoice",
                "description": "Sample GST invoice for testing"
            }
            break
    
    for filename, info in sample_files.items():
        file_path = samples_dir / filename
        if file_path.exists():
            samples.append({
                "filename": filename,
                "name": info["name"],
                "type": info["type"],
                "description": info["description"],
                "size": file_path.stat().st_size if file_path.exists() else 0
            })
    
    return {"samples": samples}


@app.get("/v1/samples/{filename}")
def download_sample_document(filename: str):
    """Download a sample document for testing."""
    # Security: only allow specific filenames
    allowed_files = {
        "GSTR1.pdf", "GSTR-3B.pdf", "sales_register.csv", 
        "purchase_register_complex.csv", "purchase_register_dirty.csv",
        "sample_invoice.txt", "GSTN.pdf"
    }
    
    if filename not in allowed_files:
        raise HTTPException(status_code=404, detail="Sample file not found")
    
    samples_dir = Path("/app/samples") if Path("/app/samples").exists() else Path(__file__).parent.parent.parent / "samples"
    file_path = samples_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Sample file not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/pdf" if filename.endswith(".pdf") else "text/csv" if filename.endswith(".csv") else "text/plain"
    )
