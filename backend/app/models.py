from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    key = Column(String(128), unique=True, index=True, nullable=False)
    label = Column(String(128), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    job_id = Column(String(64), unique=True, index=True, nullable=False)
    api_key = Column(String(128), index=True, nullable=False)
    status = Column(String(32), default="queued")
    doc_type = Column(String(32), default="invoice")
    storage_key = Column(String(512), nullable=False)  # S3 key or local path
    result = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class Webhook(Base):
    __tablename__ = "webhooks"
    id = Column(Integer, primary_key=True)
    api_key = Column(String(128), index=True, nullable=False, unique=True)
    url = Column(String(1024), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Usage(Base):
    __tablename__ = "usage"
    id = Column(Integer, primary_key=True)
    api_key = Column(String(128), index=True, nullable=False)
    month = Column(String(7), index=True)  # YYYY-MM
    docs = Column(Integer, default=0)
    ocr_pages = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)
