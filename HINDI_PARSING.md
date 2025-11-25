# Hindi Parsing Support

This document describes the Hindi parsing feature added to the docparser project.

## Overview

Hindi parsing support has been added to enable parsing of Hindi-language documents (invoices, receipts, etc.) and mixed Hindi-English documents. The implementation includes:

1. **Hindi OCR Support**: Uses Tesseract OCR with Hindi language pack (`hin+eng` for mixed documents)
2. **Hindi Regex Patterns**: Pattern matching for Hindi keywords (चालान, बिल, कुल, etc.)
3. **Hindi Detection**: Document type detection using Hindi keywords
4. **API Integration**: Hindi mode can be enabled via API parameter

## How to Use

### API Endpoint

Add the `use_hindi` form parameter to enable Hindi parsing:

```bash
curl -X POST "https://your-api.com/v1/parse" \
  -H "X-API-Key: your-api-key" \
  -F "file=@hindi_invoice.pdf" \
  -F "use_hindi=true"
```

**Parameters:**
- `use_hindi`: Accepts `"true"`, `"1"`, `"yes"`, or `"on"` to enable Hindi parsing (case-insensitive)

### Supported Document Types

Hindi parsing is implemented for the following document types:

1. **Invoices** (`invoice`): 
   - Invoice numbers (चालान संख्या, बिल नंबर)
   - Totals (कुल, कुल राशि)
   - Subtotals (उप-कुल)
   - Tax types (CGST/सीजीएसटी, SGST/एसजीएसटी, IGST/आईजीएसटी)
   - GSTIN extraction
   - Dates, HSN/SAC codes

2. **Receipts** (`receipt`):
   - Merchant names
   - Totals (कुल, कुल राशि)
   - Subtotals (उप-कुल)
   - Tax amounts (सीजीएसटी, एसजीएसटी, आईजीएसटी)
   - Line items
   - Dates

3. **Utility Bills** (`utility_bill`):
   - Provider names
   - Account numbers (खाता संख्या, खाता नंबर)
   - Amount due (राशि देय, कुल देय)
   - Due dates (देय तिथि, अंतिम भुगतान तिथि)
   - Service periods (सेवा अवधि)

4. **E-way Bills** (`eway_bill`):
   - E-way bill numbers (ई-वे बिल संख्या)
   - Vehicle numbers (वाहन संख्या)
   - Transporter GSTIN (परिवहनकर्ता जीएसटीआईएन)
   - Driver details (चालक का नाम, चालक मोबाइल)
   - Distance (दूरी)
   - From/To places (से, तक, मूल स्थान, गंतव्य)
   - Invoice references (चालान संख्या, चालान तिथि)

5. **GST Invoices** (`gst_invoice`): Uses the same Hindi rules as invoices

**Note**: Bank statements primarily use numeric data and standard banking terms, so they work with Hindi OCR but don't require separate Hindi parsing rules. Other document types (GSTR, purchase/sales registers) can be extended similarly if needed.

## Implementation Details

### Files Added/Modified

1. **`api/app/parsers/common.py`**:
   - Added `ocr_page()` with language parameter support
   - Added `extract_text_safely_hindi()` for Hindi-aware text extraction

2. **`api/app/parsers/rules_hindi.py`** (NEW):
   - Hindi regex patterns for invoice parsing
   - Hindi keywords: चालान, बिल, कुल, सीजीएसटी, etc.
   - `parse_text_rules_hindi()` function

3. **`api/app/parsers/receipt_hindi.py`** (NEW):
   - Hindi parsing rules for receipts
   - Hindi keywords: कुल, उप-कुल, रसीद, etc.

4. **`api/app/parsers/utility_bill_hindi.py`** (NEW):
   - Hindi parsing rules for utility bills
   - Hindi keywords: खाता संख्या, देय तिथि, राशि देय, etc.

5. **`api/app/parsers/eway_bill_hindi.py`** (NEW):
   - Hindi parsing rules for e-way bills
   - Hindi keywords: ई-वे बिल, वाहन संख्या, परिवहनकर्ता, etc.

6. **`api/app/parsers/detect.py`**:
   - Added Hindi detection patterns for document type detection
   - Hindi keywords for invoice, eway_bill, gstr, etc.

7. **`api/app/parsers/invoice.py`**:
   - Added `use_hindi` parameter to `parse_bytes_to_result()`
   - Uses Hindi text extraction and parsing rules when enabled

8. **`api/app/parsers/router.py`**:
   - Added `use_hindi` parameter to `parse_any()`
   - Routes to Hindi parsing rules for all supported document types when enabled
   - Imports and uses Hindi parsers for receipt, utility_bill, eway_bill, invoice, gst_invoice

9. **`api/app/main.py`**:
   - Added `use_hindi` form parameter to `/v1/parse` endpoint
   - Stores Hindi flag in job metadata

10. **`api/app/worker.py`**:
    - Reads `use_hindi` from job metadata and passes to parser

## Hindi Keywords Supported

### Invoice Terms
- **Invoice**: चालान, बिल, इनवॉइस
- **Invoice Number**: चालान संख्या, बिल नंबर
- **Total**: कुल, कुल राशि, टोटल
- **Subtotal**: उप-कुल, सबटोटल

### Tax Terms
- **CGST**: सीजीएसटी
- **SGST**: एसजीएसटी
- **IGST**: आईजीएसटी
- **GST**: जीएसटी, कर

### Receipt Terms
- **Receipt**: रसीद
- **Total**: कुल, कुल राशि
- **Subtotal**: उप-कुल

### Utility Bill Terms
- **Account Number**: खाता संख्या, खाता नंबर
- **Amount Due**: राशि देय, कुल देय, शेष देय
- **Due Date**: देय तिथि, अंतिम भुगतान तिथि
- **Service Period**: सेवा अवधि

### E-way Bill Terms
- **E-way Bill**: ई-वे बिल, वे बिल
- **Vehicle Number**: वाहन संख्या, वाहन नंबर
- **Transporter GSTIN**: परिवहनकर्ता जीएसटीआईएन
- **Driver Name**: चालक का नाम
- **Driver Mobile**: चालक मोबाइल, चालक फोन
- **Distance**: दूरी
- **From/To**: से, तक, मूल स्थान, गंतव्य
- **Valid Until**: वैध तक, वैध जब तक

### Document Types
- **E-way Bill**: ई-वे बिल, वे बिल
- **GST Return**: जीएसटी रिटर्न, जीएसटी दाखिल
- **Purchase Register**: खरीद रजिस्टर

## Requirements

### Tesseract Hindi Language Pack

For Hindi OCR to work, you need to install the Tesseract Hindi language pack:

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr-hin
```

**macOS:**
```bash
brew install tesseract-lang
```

**Windows:**
Download from: https://github.com/tesseract-ocr/tessdata

The system will automatically fallback to English-only OCR if the Hindi language pack is not installed.

## Extending to Other Document Types

To add Hindi support for other document types (receipt, utility_bill, etc.):

1. Create a Hindi rules file (e.g., `receipt_hindi.py`) with Hindi regex patterns
2. Add Hindi detection keywords to `detect.py`
3. Update `router.py` to use Hindi rules when `use_hindi=True` for that document type
4. Follow the same pattern as `rules_hindi.py` for the new document type

## Testing

To test Hindi parsing:

1. Prepare a Hindi or mixed Hindi-English document (PDF or image)
2. Send a POST request to `/v1/parse` with `use_hindi=true`
3. Check the response for parsed fields in Hindi text

Example test:
```bash
curl -X POST "http://localhost:8000/v1/parse" \
  -H "X-API-Key: test-key" \
  -F "file=@test_hindi_invoice.pdf" \
  -F "use_hindi=true"
```

## Notes

- Hindi parsing works best with documents that have clear Hindi text
- Mixed Hindi-English documents are supported (OCR uses `hin+eng` mode)
- If Hindi language pack is not installed, the system falls back to English-only parsing
- The `use_hindi` flag is stored in job metadata and persists through the parsing pipeline

