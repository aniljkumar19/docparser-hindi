# Bulk processing database schema additions

from sqlalchemy import Column, String, JSON, TIMESTAMP, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

# Add to existing db.py

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
    
    # Relationships
    jobs = relationship("Job", back_populates="batch")

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

# Update existing Job model
class Job(Base):
    # ... existing fields ...
    batch_id = Column(String, ForeignKey("batches.id"), nullable=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=True)
    
    # Relationships
    batch = relationship("Batch", back_populates="jobs")
    client = relationship("Client", back_populates="jobs")

