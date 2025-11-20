# Dashboard Components

React/TypeScript components for Block 1 features: Validation and ITC Reconciliation.

## Components

### 1. ValidationPanel

Displays validation issues for canonical documents (sales_register, gstr2b, gstr3b).

**Usage:**
```tsx
import { ValidationPanel } from '../components/ValidationPanel';

<ValidationPanel 
  docType="sales_register" 
  jobId="job_123" 
/>
```

**Props:**
- `docType`: `"sales_register" | "gstr2b" | "gstr3b"`
- `jobId`: Job ID string

**Features:**
- Automatically fetches validation results from `/v1/validate/{docType}/{jobId}`
- Shows success message if no issues
- Displays warnings and errors with color coding
- Shows issue codes and messages

### 2. ItcReconciliationPanel

Displays ITC reconciliation between GSTR-2B (available) and GSTR-3B (claimed).

**Usage:**
```tsx
import { ItcReconciliationPanel } from '../components/ItcReconciliationPanel';

<ItcReconciliationPanel 
  job2bId="job_2b_123" 
  job3bId="job_3b_456" 
/>
```

**Props:**
- `job2bId`: GSTR-2B job ID (string | null)
- `job3bId`: GSTR-3B job ID (string | null)

**Features:**
- Shows GSTIN and period
- Overall ITC status (match/over-claimed/under-claimed)
- Detailed table by tax head (IGST, CGST, SGST, CESS)
- Lists reconciliation issues

### 3. ExportSalesRegisterButton

Button to export sales register to CSV (canonical or legacy format).

**Usage:**
```tsx
import { ExportSalesRegisterButton } from '../components/ExportSalesRegisterButton';

<ExportSalesRegisterButton 
  jobId="job_123" 
  variant="canonical" 
/>
```

**Props:**
- `jobId`: Job ID string
- `variant`: `"canonical" | "legacy"` (default: "canonical")

**Features:**
- Downloads CSV file directly
- Supports both canonical and legacy formats
- Handles errors gracefully

## API Endpoints Used

- `GET /v1/validate/{docType}/{jobId}` - Validation endpoint
- `GET /v1/reconcile/itc/2b-3b?job2b_id=...&job3b_id=...` - ITC reconciliation
- `GET /v1/export/sales-csv-canonical/{jobId}` - Canonical CSV export
- `GET /v1/export/sales-csv/{jobId}` - Legacy CSV export

## Integration Example

Add to your document detail page:

```tsx
// In dashboard.tsx or similar
import { ValidationPanel } from '../components/ValidationPanel';
import { ExportSalesRegisterButton } from '../components/ExportSalesRegisterButton';
import { ItcReconciliationPanel } from '../components/ItcReconciliationPanel';

// For sales register
{selectedJob?.doc_type === "sales_register" && (
  <>
    <ValidationPanel 
      docType="sales_register" 
      jobId={selectedJob.job_id} 
    />
    <ExportSalesRegisterButton jobId={selectedJob.job_id} />
  </>
)}

// For ITC reconciliation (when both 2B and 3B are available)
{selectedJob?.doc_type === "gstr2b" && gstr3bJobId && (
  <ItcReconciliationPanel 
    job2bId={selectedJob.job_id} 
    job3bId={gstr3bJobId} 
  />
)}
```

## Notes

- All components automatically use API key from `localStorage.getItem("docparser_api_key")`
- Falls back to `NEXT_PUBLIC_DOCPARSER_API_KEY` env var or "dev_123" for development
- Uses `getApiBase()` utility for environment-aware API URL resolution

