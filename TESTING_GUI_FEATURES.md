# Testing New Features in GUI

## How to Test the New Features

### 1. **GSTR-3B & GSTR-2B → Canonical Format**

**Both GSTR-3B and GSTR-2B work with canonical format!**

#### GSTR-3B (Summary-level entries):
**Steps:**
1. Upload a GSTR-3B document (PDF or image)
2. Wait for parsing to complete
3. In the "Parsed JSON" tab, toggle **"Canonical Format (v0.1)"**
4. You should see:
   - `schema_version: "doc.v0.1"`
   - `doc_type: "gstr3b"`
   - Summary entries (e.g., "OUTWARD", "REVERSE_CHARGE")
   - Aggregated totals in `financials`

#### GSTR-2B (Invoice-level entries) - **NEW FEATURE**:
**Steps:**
1. Upload a GSTR-2B document (PDF or image)
2. Wait for parsing to complete
3. In the "Parsed JSON" tab, toggle **"Canonical Format (v0.1)"**
4. You should see:
   - `schema_version: "doc.v0.1"`
   - `doc_type: "gst_return"`
   - **Invoice-level entries** in the `entries[]` array (one per invoice)
   - Each entry has `entry_id`, `entry_number`, `party`, `amounts`, etc.

**What to check for GSTR-2B:**
- Each invoice from `b2b`, `b2bur`, `imps` sections appears as a separate entry
- Party information (supplier name, GSTIN, state code) is preserved
- Tax breakdown (CGST, SGST, IGST, CESS) is correct
- `doc_specific` contains section name, ITC availability, place of supply

**Key Difference:**
- **GSTR-3B**: Summary entries (aggregated by supply type)
- **GSTR-2B**: Invoice-level entries (one entry per invoice from suppliers)

---

### 2. **Sales Register Validator**

**Steps:**
1. Upload a sales register document (CSV or PDF)
2. Wait for parsing to complete
3. Select the job in the dashboard
4. Click the **"Validate"** button (blue button with ✓ icon)
5. Validation runs automatically when you select a sales register job

**What to check:**
- If totals match: Green message "✓ No validation issues found"
- If there are mismatches: Yellow/red boxes showing:
  - Issue code (e.g., `GRAND_TOTAL_MISMATCH`)
  - Level (warning/error)
  - Message explaining the issue
  - Metadata (entry_id if applicable)

**Validation checks:**
- Per-entry: `total ≈ taxable + taxes`
- Global: `financials.subtotal` vs sum of entries
- Global: `financials.tax_breakup` vs sum of entry taxes
- Global: `financials.grand_total` vs `subtotal + tax_total`

---

### 3. **Canonical CSV Export**

**Steps:**
1. Upload a sales register document
2. Wait for parsing to complete
3. In the "Exports" tab, click **"Canonical CSV"** button (purple button with 📋 icon)
4. CSV file downloads with name: `sales_canonical_{job_id}.csv`

**What to check:**
- CSV opens in Excel
- Headers: Entry ID, Invoice No, Invoice Date, Customer Name, Customer GSTIN, Customer State Code, Taxable Value, CGST, SGST, IGST, CESS, Total Invoice Value, Reverse Charge, Invoice Type, Place of Supply
- Each row represents one invoice entry
- All values are properly formatted

**Compare with:**
- Regular "Sales CSV" export (legacy format)
- Canonical format has more structured columns (Entry ID, Customer State Code, etc.)

---

### 4. **Testing All Together**

**Complete workflow:**
1. Upload a sales register CSV/PDF
2. Toggle "Canonical Format" to see structured data
3. Click "Validate" to check for issues
4. If valid, export "Canonical CSV"
5. Open CSV in Excel and verify data

**For GSTR-2B:**
1. Upload GSTR-2B document
2. Toggle "Canonical Format"
3. Verify invoice-level entries are shown
4. Check that each entry has supplier info and tax breakdown

---

## API Endpoints Added

### New Endpoints:

1. **`GET /v1/export/sales-csv-canonical/{job_id}`**
   - Exports sales register in canonical format to CSV
   - Requires API key authentication

2. **`GET /v1/validate/sales-register/{job_id}`**
   - Validates a sales register job
   - Returns validation issues with codes, levels, and messages
   - Requires API key authentication

### Existing Endpoints (Updated):

- **`GET /v1/jobs/{job_id}?format=canonical`**
   - Returns canonical format when `format=canonical` is specified
   - Works for all document types (invoice, sales_register, purchase_register, gstr3b, gstr2b, etc.)

---

## Troubleshooting

**Validation not showing:**
- Make sure the job is a `sales_register` type
- Check browser console for errors
- Verify API key is set

**Canonical CSV not downloading:**
- Check that job status is "succeeded"
- Verify it's a sales_register document
- Check browser console for API errors

**Canonical format not appearing:**
- Toggle the "Canonical Format (v0.1)" checkbox
- Check that the job has a valid result
- Verify the document type is supported (invoice, sales_register, purchase_register, gstr3b, gstr2b)

---

## Sample Test Data

You can test with:
- Sales register CSV files
- GSTR-2B PDFs
- Any document that parses as `sales_register` or `gstr2b`

The dashboard will automatically:
- Show canonical format when toggled
- Run validation for sales registers
- Provide export buttons for supported formats

