from pydantic import BaseModel
from typing import Optional, Dict, Any

class JobResponse(BaseModel):
    job_id: str
    status: str
    doc_type: str = "invoice"
    result: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = {}

class WebhookRegistration(BaseModel):
    url: str

class UsageResponse(BaseModel):
    month: str
    docs_parsed: int
    ocr_pages: int
