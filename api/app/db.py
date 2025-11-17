import os, uuid
from sqlalchemy import create_engine, Column, String, JSON, TIMESTAMP, Integer, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import secrets



# Railway provides DATABASE_URL automatically, but we also support DB_URL for flexibility
DB_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL", "sqlite:///./doc.db")

# Schema name for DocParser tables (isolates from other apps in same database)
# Set DOCPARSER_SCHEMA env var to change, defaults to 'docparser'
# Note: SQLite doesn't support schemas, so schema is only used for PostgreSQL
DOCPARSER_SCHEMA = os.getenv("DOCPARSER_SCHEMA", "docparser")

# Only use schema for PostgreSQL (SQLite doesn't support schemas)
USE_SCHEMA = DB_URL.startswith("postgresql") or DB_URL.startswith("postgres")

# For SQLite, don't use schema (set to None)
TABLE_SCHEMA = DOCPARSER_SCHEMA if USE_SCHEMA else None

engine = create_engine(DB_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = {'schema': TABLE_SCHEMA} if TABLE_SCHEMA else {}
    id = Column(String, primary_key=True, default=lambda: "job_" + uuid.uuid4().hex[:12])
    status = Column(String, default="queued")
    doc_type = Column(String, default="invoice")
    object_key = Column(String)
    tenant_id = Column(String, default="")   # <— new
    api_key = Column(String, default="")
    filename = Column(String, default="")
    result = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    batch_id = Column(String, nullable=True)  # NEW: Link to batch
    client_id = Column(String, nullable=True)  # NEW: Link to client
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

class Batch(Base):
    """Represents a batch of documents uploaded together"""
    __tablename__ = "batches"
    __table_args__ = {'schema': TABLE_SCHEMA} if TABLE_SCHEMA else {}
    
    id = Column(String, primary_key=True, default=lambda: "batch_" + uuid.uuid4().hex[:12])
    tenant_id = Column(String, nullable=False)
    client_id = Column(String, nullable=True)  # Optional client grouping
    batch_name = Column(String, nullable=True)  # User-defined batch name
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    status = Column(String, default="processing")  # processing, completed, failed
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

class Client(Base):
    """CA's clients"""
    __tablename__ = "clients"
    __table_args__ = {'schema': TABLE_SCHEMA} if TABLE_SCHEMA else {}
    
    id = Column(String, primary_key=True, default=lambda: "client_" + uuid.uuid4().hex[:12])
    tenant_id = Column(String, nullable=False)  # CA firm ID
    name = Column(String, nullable=False)
    gstin = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

def init_db():
    """Initialize database: create schema if needed, then create tables."""
    # Only create schema for PostgreSQL (not SQLite)
    if USE_SCHEMA:
        try:
            with engine.connect() as conn:
                # Create schema if it doesn't exist (idempotent)
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DOCPARSER_SCHEMA}"))
                conn.commit()
        except Exception as e:
            import logging
            logging.warning(f"Could not create schema {DOCPARSER_SCHEMA}: {e}")

    Base.metadata.create_all(bind=engine)

def create_job(
    db,
    *,
    object_key: str,
    api_key: str,
    tenant_id: str,
    filename: str,
    meta: dict | None = None,
):
    job = Job(
        object_key=object_key,
        api_key=api_key,
        tenant_id=tenant_id or "",
        filename=filename,
        status="queued",
        result=None,
        meta=meta or {},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job



def get_job_by_id(db, job_id: str):
    return db.get(Job, job_id)

def update_job_status(db, job_id: str, **kwargs):
    j = db.get(Job, job_id)
    if not j:
        return None
    for k, v in kwargs.items():
        setattr(j, k, v)
    db.add(j); db.commit(); db.refresh(j)
    return j

def get_metered_item_for_tenant(db, tenant_id: str) -> str | None:
    if not tenant_id:
        return None
    row = db.execute(
        text("SELECT stripe_item_parse FROM tenants WHERE id = :t"),
        {"t": tenant_id},
    ).fetchone()
    return row[0] if row and row[0] else None


# Utility functions for extracting matching criteria
def _normalize_gstin(gstin: str | None) -> str | None:
    """Normalize GSTIN: strip whitespace and convert to uppercase."""
    if not gstin:
        return None
    if isinstance(gstin, dict):
        gstin = gstin.get("value") or gstin.get("gstin")
    if not isinstance(gstin, str):
        return None
    return gstin.strip().upper()

def _extract_period_from_result(result: dict) -> tuple[int | None, int | None]:
    """Extract period month and year from parsed result.
    Returns (month, year) or (None, None) if not found.
    Handles different period formats:
    - GSTR-1: {"period": {"month": 11, "year": 2025}}
    - Sales register: {"period": {"from": "2025-11-01", "to": "2025-11-30"}}
    - Or: {"period": "November 2025"}
    """
    if not isinstance(result, dict):
        return (None, None)
    
    period = result.get("period")
    if not period:
        return (None, None)
    
    # Handle dict format: {"month": 11, "year": 2025}
    if isinstance(period, dict):
        month = period.get("month")
        year = period.get("year")
        if month and year:
            return (int(month), int(year))
        
        # Handle date range format: {"from": "2025-11-01", "to": "2025-11-30"}
        from_date = period.get("from")
        if from_date:
            try:
                dt = datetime.strptime(from_date[:10], "%Y-%m-%d")
                return (dt.month, dt.year)
            except:
                pass
    
    # Handle string format: "November 2025" or "2025-11"
    if isinstance(period, str):
        try:
            # Try various formats
            for fmt in ["%B %Y", "%b %Y", "%Y-%m", "%m/%Y", "%Y/%m"]:
                try:
                    dt = datetime.strptime(period.strip(), fmt)
                    return (dt.month, dt.year)
                except:
                    continue
        except:
            pass
    
    return (None, None)

def _extract_gstin_from_result(result: dict) -> str | None:
    """Extract GSTIN from parsed result, handling different formats."""
    if not isinstance(result, dict):
        return None
    
    # Try direct gstin field
    gstin = result.get("gstin")
    if gstin:
        return _normalize_gstin(gstin)
    
    # Try seller.gstin (for invoices)
    seller = result.get("seller")
    if isinstance(seller, dict):
        gstin = seller.get("gstin")
        if gstin:
            return _normalize_gstin(gstin)
    
    return None

# Utility selectors
def get_latest_job_by_doc_type(db, tenant_id: str, doc_type: str):
    from sqlalchemy import or_
    # For development: if tenant_id is provided, also search for empty tenant_id
    # This helps when jobs were created with different tenant_ids
    if tenant_id:
        # Search for jobs matching tenant_id OR empty tenant_id (for development)
        query = db.query(Job).filter(
            or_(Job.tenant_id == tenant_id, Job.tenant_id == "", Job.tenant_id.is_(None)),
            Job.doc_type == doc_type,
            Job.status == "succeeded",
            Job.result.isnot(None),
        )
    else:
        # If no tenant_id, only search for empty tenant_id
        query = db.query(Job).filter(
            or_(Job.tenant_id == "", Job.tenant_id.is_(None)),
            Job.doc_type == doc_type,
            Job.status == "succeeded",
            Job.result.isnot(None),
        )
    return query.order_by(Job.updated_at.desc()).first()

def find_matching_job_by_gstin_and_period(
    db, 
    tenant_id: str, 
    target_doc_type: str,
    source_gstin: str | None,
    source_period_month: int | None,
    source_period_year: int | None,
    exclude_job_id: str | None = None
):
    """Find a matching job by GSTIN and period, regardless of upload order.
    
    Args:
        db: Database session
        tenant_id: Tenant ID to filter by
        target_doc_type: The doc_type to search for (e.g., "gstr1" or "sales_register")
        source_gstin: GSTIN from the source document (normalized)
        source_period_month: Period month from source (1-12)
        source_period_year: Period year from source (e.g., 2025)
        exclude_job_id: Job ID to exclude from search
    
    Returns:
        Matching Job or None
    """
    from sqlalchemy import or_
    
    if not source_gstin or not source_period_month or not source_period_year:
        return None
    
    # Build query - use or_ for status to handle multiple statuses
    status_filter = or_(Job.status == "succeeded", Job.status == "needs_review")
    
    if tenant_id:
        query = db.query(Job).filter(
            or_(Job.tenant_id == tenant_id, Job.tenant_id == "", Job.tenant_id.is_(None)),
            Job.doc_type == target_doc_type,
            status_filter,  # Include needs_review status
            Job.result.isnot(None),
        )
    else:
        query = db.query(Job).filter(
            or_(Job.tenant_id == "", Job.tenant_id.is_(None)),
            Job.doc_type == target_doc_type,
            status_filter,
            Job.result.isnot(None),
        )
    
    if exclude_job_id:
        query = query.filter(Job.id != exclude_job_id)
    
    # Get all candidates and filter by GSTIN and period in Python
    # (SQLAlchemy JSON queries can be complex, so we do it in Python for reliability)
    candidates = query.order_by(Job.updated_at.desc()).all()
    
    for job in candidates:
        if not job.result:
            continue
        
        # Extract GSTIN and period from this job's result
        job_gstin = _extract_gstin_from_result(job.result)
        job_period_month, job_period_year = _extract_period_from_result(job.result)
        
        # Check if GSTIN matches (normalized)
        if job_gstin and job_gstin == source_gstin:
            # Check if period matches
            if job_period_month == source_period_month and job_period_year == source_period_year:
                return job
    
    return None

# Bulk processing functions
def create_batch(db, *, tenant_id: str, client_id: str = None, batch_name: str = None, total_files: int):
    batch = Batch(
        tenant_id=tenant_id,
        client_id=client_id,
        batch_name=batch_name,
        total_files=total_files,
        status="processing"
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch

def get_batch_by_id(db, batch_id: str):
    return db.get(Batch, batch_id)

def get_jobs_by_batch(db, batch_id: str):
    return db.query(Job).filter(Job.batch_id == batch_id).all()

def update_batch_stats(db, batch_id: str, **kwargs):
    """Update batch statistics (processed_files, failed_files, etc.)
    Increments the current value by the provided amount.
    """
    batch = db.get(Batch, batch_id)
    if batch:
        for k, v in kwargs.items():
            if hasattr(batch, k):
                current = getattr(batch, k, 0)
                setattr(batch, k, current + v)
        db.commit()
        db.refresh(batch)
    return batch
