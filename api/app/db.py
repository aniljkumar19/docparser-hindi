import os, uuid
from sqlalchemy import create_engine, Column, String, JSON, TIMESTAMP, Integer, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import secrets



DB_URL = os.getenv("DB_URL", "sqlite:///./doc.db")
engine = create_engine(DB_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
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
    
    id = Column(String, primary_key=True, default=lambda: "client_" + uuid.uuid4().hex[:12])
    tenant_id = Column(String, nullable=False)  # CA firm ID
    name = Column(String, nullable=False)
    gstin = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

def init_db():
    Base.metadata.create_all(engine)

def generate_job_id() -> str:
    return "job_" + secrets.token_hex(6)

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
        id=generate_job_id(),
        api_key=api_key,
        tenant_id=tenant_id,     # <-- use the passed tenant_id
        object_key=object_key,
        filename=filename,
        status="queued",
        doc_type=None,
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


# Utility selectors
def get_latest_job_by_doc_type(db, tenant_id: str, doc_type: str):
    return (
        db.query(Job)
        .filter(
            Job.tenant_id == tenant_id,
            Job.doc_type == doc_type,
            Job.status == "succeeded",
            Job.result.isnot(None),
        )
        .order_by(Job.updated_at.desc())
        .first()
    )

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
    batch = db.get(Batch, batch_id)
    if batch:
        for k, v in kwargs.items():
            current = getattr(batch, k, 0)
            setattr(batch, k, current + v)
        db.commit()

def create_client(db, *, tenant_id: str, name: str, gstin: str = None, email: str = None, phone: str = None):
    client = Client(
        tenant_id=tenant_id,
        name=name,
        gstin=gstin,
        email=email,
        phone=phone
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client

def get_client_by_id(db, client_id: str):
    return db.get(Client, client_id)
