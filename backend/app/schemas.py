from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class TaxLine(BaseModel):
    type: str
    rate: float
    amount: float

class LineItem(BaseModel):
    desc: str
    qty: float
    unit_price: float
    amount: float

class ParseResult(BaseModel):
    invoice_number: Optional[Dict[str, Any]] = None
    date: Optional[Dict[str, Any]] = None
    seller: Optional[Dict[str, Any]] = None
    buyer: Optional[Dict[str, Any]] = None
    currency: Optional[str] = "INR"
    subtotal: Optional[float] = None
    taxes: List[TaxLine] = []
    total: Optional[float] = None
    line_items: List[LineItem] = []
    warnings: List[str] = []

class JobResponse(BaseModel):
    job_id: str
    status: str
    doc_type: str = "invoice"
    result: Optional[ParseResult] = None
    meta: Dict[str, Any] = {}

class WebhookRegistration(BaseModel):
    url: str

class UsageResponse(BaseModel):
    month: str
    docs_parsed: int
    ocr_pages: int
