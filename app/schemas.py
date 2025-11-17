from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Literal



# Allowed document types (include 'unknown' for newly queued jobs)
DocType = Literal["unknown", "invoice", "gst_invoice", "utility_bill", "bank_statement"]

# Allowed job statuses
Status = Literal["queued", "processing", "done", "needs_review", "error"]

class MoneyField(BaseModel):
    value: float
    confidence: float = 0.9

class TextField(BaseModel):
    value: str
    confidence: float = 0.9

class Party(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None

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
    invoice_number: Optional[TextField] = None
    date: Optional[TextField] = None
    seller: Optional[Party] = None
    buyer: Optional[Party] = None
    currency: Optional[str] = "INR"
    subtotal: Optional[float] = None
    taxes: List[TaxLine] = []
    total: Optional[float] = None
    line_items: List[LineItem] = []
    warnings: List[str] = []

class JobResponse(BaseModel):
    job_id: str
    status: str
    doc_type: str = "unknown"
    result: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = {}



class WebhookRegistration(BaseModel):
    url: str

class UsageResponse(BaseModel):
    month: str
    docs_parsed: int

# === Canonical v0 (stable output your clients can rely on) ===
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

SCHEMA_V_INVOICE = "invoice.v0"
SCHEMA_V_UTILITY = "utility_bill.v0"
SCHEMA_V_BANK    = "bank_statement.v0"

# ---------- Invoice v0 ----------
class Party(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class InvoiceLineItem(BaseModel):
    description: str
    hsn_sac: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    amount: float
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None

class InvoiceTaxBreakup(BaseModel):
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    cess: float = 0.0

class InvoiceTotals(BaseModel):
    subtotal: float
    tax_total: float
    grand_total: float
    currency: str = "INR"

class InvoiceV0(BaseModel):
    schema_version: str = Field(default=SCHEMA_V_INVOICE)
    doc_type: str = Field(default="invoice")
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None   # ISO date "YYYY-MM-DD"
    due_date: Optional[str] = None       # ISO date
    seller: Optional[Party] = None
    buyer: Optional[Party] = None
    place_of_supply: Optional[str] = None
    items: List[InvoiceLineItem] = []
    tax_breakup: InvoiceTaxBreakup = InvoiceTaxBreakup()
    totals: InvoiceTotals
    notes: Optional[str] = None
    po_number: Optional[str] = None
    meta: Dict[str, Any] = {}

# ---------- Utility Bill v0 (minimal) ----------
class UtilityCharge(BaseModel):
    name: str
    amount: float

class UtilityPeriod(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class UtilityBillV0(BaseModel):
    schema_version: str = Field(default=SCHEMA_V_INVOICE)
    doc_type: str = Field(default="invoice")
    provider: Optional[str] = None
    service_type: Optional[str] = None   # electricity/water/gas/etc
    account_number: Optional[str] = None
    bill_period: UtilityPeriod = UtilityPeriod()
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    charges: List[UtilityCharge] = []
    totals: Dict[str, Any] = {}          # {"subtotal":..., "tax_total":..., "grand_total":..., "currency":"INR"}
    meta: Dict[str, Any] = {}

# ---------- Bank Statement v0 (minimal) ----------
class BankTxn(BaseModel):
    date: str                     # ISO date
    narration: str
    amount: float
    type: str                     # "credit" | "debit"
    balance: Optional[float] = None
    reference: Optional[str] = None
    counterparty: Optional[str] = None

class BankStatementV0(BaseModel):
    schema_version: str = Field(default=SCHEMA_V_INVOICE)
    doc_type: str = Field(default="invoice")
    bank_name: Optional[str] = None
    account_holder: Optional[str] = None
    account_number: Optional[str] = None
    ifsc: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    currency: str = "INR"
    transactions: List[BankTxn] = []
    meta: Dict[str, Any] = {}



# --- JSON Schema for invoice.v0 (clients can validate against this) ---
INVOICE_V0_SCHEMA = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://docparser.local/schemas/invoice.v0.json",
  "title": "Invoice v0",
  "type": "object",
  "additionalProperties": False,
  "properties": {
    "schema_version": {"const": "invoice.v0"},
    "doc_type": {"const": "invoice"},
    "invoice_number": {"type": ["string", "null"]},
    "invoice_date": {"type": ["string", "null"]},  # ISO date "YYYY-MM-DD"
    "due_date": {"type": ["string", "null"]},
    "seller": {
      "type": ["object", "null"],
      "additionalProperties": True
    },
    "buyer": {
      "type": ["object", "null"],
      "additionalProperties": True
    },
    "place_of_supply": {"type": ["string", "null"]},
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
          "description": {"type": "string"},
          "hsn_sac": {"type": ["string", "null"]},
          "quantity": {"type": ["number", "null"]},
          "unit": {"type": ["string", "null"]},
          "unit_price": {"type": ["number", "null"]},
          "amount": {"type": "number"},
          "tax_rate": {"type": ["number", "null"]},
          "tax_amount": {"type": ["number", "null"]}
        },
        "required": ["description", "amount"]
      }
    },
    "tax_breakup": {
      "type": "object",
      "additionalProperties": False,
      "properties": {
        "cgst": {"type": "number"},
        "sgst": {"type": "number"},
        "igst": {"type": "number"},
        "cess": {"type": "number"}
      },
      "required": ["cgst", "sgst", "igst", "cess"]
    },
    "totals": {
      "type": "object",
      "additionalProperties": False,
      "properties": {
        "subtotal": {"type": "number"},
        "tax_total": {"type": "number"},
        "grand_total": {"type": "number"},
        "currency": {"type": "string"}
      },
      "required": ["subtotal", "tax_total", "grand_total", "currency"]
    },
    "notes": {"type": ["string", "null"]},
    "po_number": {"type": ["string", "null"]},
    "meta": {
      "type": "object",
      "additionalProperties": True
    }
  },
  "required": ["schema_version", "doc_type", "items", "tax_breakup", "totals", "meta"]
}


