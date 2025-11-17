# Bulk processing API endpoints

from fastapi import FastAPI, UploadFile, File, Header, HTTPException, status, Form
from typing import List, Optional
from sqlalchemy.orm import Session
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

# Add to main.py

@app.post("/v1/bulk-parse")
async def bulk_parse_endpoint(
    files: List[UploadFile] = File(...),
    client_id: Optional[str] = Form(None),
    batch_name: Optional[str] = Form(None),
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key"),
):
    """
    Upload and parse multiple documents in a single batch
    """
    api_key, tenant_id = verify_api_key(authorization, x_api_key)
    
    if len(files) > 100:  # Limit bulk uploads
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 files allowed per batch"
        )
    
    # Create batch record
    with SessionLocal() as db:
        batch = create_batch(
            db, 
            tenant_id=tenant_id,
            client_id=client_id,
            batch_name=batch_name,
            total_files=len(files)
        )
        
        # Process files in parallel
        job_ids = []
        for file in files:
            try:
                contents = await file.read()
                mb = len(contents) / (1024 * 1024)
                
                if mb > MAX_FILE_MB:
                    # Log error but continue with other files
                    update_batch_stats(db, batch.id, failed_files=1)
                    continue
                
                # Save file to S3
                object_key = get_object_key(file.filename)
                save_file_to_s3(object_key, contents)
                
                # Create job linked to batch
                job = create_job(
                    db,
                    object_key=object_key,
                    filename=file.filename,
                    tenant_id=tenant_id,
                    api_key=api_key,
                    batch_id=batch.id,
                    client_id=client_id
                )
                
                job_ids.append(job.id)
                
                # Enqueue for processing
                enqueue_parse(q, job.id)
                
            except Exception as e:
                # Log error but continue
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

@app.get("/v1/batches/{batch_id}/export")
async def export_batch_results(
    batch_id: str,
    format: str = "json",  # json, csv, tally_xml, tally_csv
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key"),
):
    """Export batch results in various formats"""
    api_key, tenant_id = verify_api_key(authorization, x_api_key)
    
    with SessionLocal() as db:
        batch = get_batch_by_id(db, batch_id)
        if not batch or batch.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        jobs = get_jobs_by_batch(db, batch_id)
        successful_jobs = [job for job in jobs if job.status == "succeeded" and job.result]
        
        if format == "json":
            return {
                "batch_id": batch.id,
                "total_documents": len(jobs),
                "successful_documents": len(successful_jobs),
                "results": [job.result for job in successful_jobs]
            }
        
        elif format == "csv":
            # Generate CSV export
            csv_data = generate_batch_csv(successful_jobs)
            return {"csv_data": csv_data}
        
        elif format == "tally_xml":
            # Generate Tally XML for all successful invoices
            tally_xml = generate_batch_tally_xml(successful_jobs)
            return {"tally_xml": tally_xml}
        
        elif format == "tally_csv":
            # Generate Tally CSV for all successful invoices
            tally_csv = generate_batch_tally_csv(successful_jobs)
            return {"tally_csv": tally_csv}
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

# Helper functions
def create_batch(db: Session, tenant_id: str, client_id: Optional[str], 
                batch_name: Optional[str], total_files: int):
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

def get_batch_by_id(db: Session, batch_id: str):
    return db.get(Batch, batch_id)

def get_jobs_by_batch(db: Session, batch_id: str):
    return db.query(Job).filter(Job.batch_id == batch_id).all()

def update_batch_stats(db: Session, batch_id: str, **kwargs):
    batch = db.get(Batch, batch_id)
    if batch:
        for k, v in kwargs.items():
            current = getattr(batch, k, 0)
            setattr(batch, k, current + v)
        db.commit()

def generate_batch_csv(jobs):
    """Generate CSV export for batch results"""
    import csv
    from io import StringIO
    
    buf = StringIO()
    writer = csv.writer(buf)
    
    # Header
    writer.writerow([
        "Job ID", "Filename", "Invoice Number", "Date", "Seller GSTIN", 
        "Buyer GSTIN", "Total Amount", "CGST", "SGST", "IGST", "Status"
    ])
    
    for job in jobs:
        result = job.result or {}
        writer.writerow([
            job.id,
            job.filename,
            result.get("invoice_number", {}).get("value", "") if isinstance(result.get("invoice_number"), dict) else result.get("invoice_number", ""),
            result.get("date", {}).get("value", "") if isinstance(result.get("date"), dict) else result.get("date", ""),
            result.get("seller", {}).get("gstin", ""),
            result.get("buyer", {}).get("gstin", ""),
            result.get("total", ""),
            sum(t.get("amount", 0) for t in result.get("taxes", []) if t.get("type") == "CGST"),
            sum(t.get("amount", 0) for t in result.get("taxes", []) if t.get("type") == "SGST"),
            sum(t.get("amount", 0) for t in result.get("taxes", []) if t.get("type") == "IGST"),
            job.status
        ])
    
    return buf.getvalue()

def generate_batch_tally_xml(jobs):
    """Generate Tally XML for batch results"""
    from .exporters.tally_xml import invoice_to_tally_xml
    
    xml_parts = []
    for job in jobs:
        if job.result:
            xml_parts.append(invoice_to_tally_xml(job.result))
    
    return "\n".join(xml_parts)

def generate_batch_tally_csv(jobs):
    """Generate Tally CSV for batch results"""
    from .exporters.tally_csv import invoice_to_tally_csv
    
    csv_parts = []
    for job in jobs:
        if job.result:
            csv_parts.append(invoice_to_tally_csv(job.result))
    
    return "\n".join(csv_parts)

