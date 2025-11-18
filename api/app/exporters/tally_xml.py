from typing import Dict, Any
from xml.sax.saxutils import escape
import logging
import xml.etree.ElementTree as ET

def _format_tally_date(date_str: str) -> str:
    """Convert date from YYYY-MM-DD to YYYYMMDD format for Tally"""
    if not date_str:
        return ""
    # Remove hyphens and any time portion
    date_str = str(date_str).strip()
    if "T" in date_str:
        date_str = date_str.split("T")[0]
    return date_str.replace("-", "")

def _extract_state_code(gstin: str) -> str | None:
    """Extract state code (first 2 digits) from GSTIN"""
    if not gstin or len(gstin) < 2:
        return None
    try:
        return gstin[:2]
    except:
        return None

def invoice_to_tally_xml(parsed: Dict[str, Any], voucher_type: str = "Sales", company_state_code: str | None = None) -> str:
    """
    Generate Tally XML for a single invoice/voucher.
    
    Args:
        parsed: Parsed invoice/register entry data
        voucher_type: "Sales" or "Purchase" - determines voucher type and ledger structure
        company_state_code: Company's state code (first 2 digits of GSTIN) for GST type validation
    """
    inv_no = (parsed.get("invoice_number") or {}).get("value") if isinstance(parsed.get("invoice_number"), dict) else parsed.get("invoice_number")
    date = (parsed.get("date") or {}).get("value") if isinstance(parsed.get("date"), dict) else parsed.get("date")
    buyer = parsed.get("buyer") or {}
    party_name = escape(str(buyer.get("name") or "Buyer"))
    gstin_raw = str(buyer.get("gstin") or "")
    gstin = escape(gstin_raw)  # Escaped for XML
    
    # Normalize stock item name (remove trailing spaces, ensure consistent casing)
    stock_item_name = "Invoice Item"  # Default, can be made configurable
    
    # Format date for Tally (YYYYMMDD)
    formatted_date = _format_tally_date(date or "")

    stock_items = []
    for li in parsed.get("line_items", []):
        desc = escape(str(li.get("desc", "Item")))
        # Normalize stock item name: trim spaces, consistent casing
        desc_normalized = desc.strip()
        if not desc_normalized:
            desc_normalized = stock_item_name
        qty = li.get("qty", 0)
        rate = li.get("unit_price", 0)
        amount = li.get("amount", 0)
        stock_items.append(f"""
            <ALLINVENTORYENTRIES.LIST>
              <STOCKITEMNAME>{desc_normalized}</STOCKITEMNAME>
              <ACTUALQTY>{qty}</ACTUALQTY>
              <BILLEDQTY>{qty}</BILLEDQTY>
              <RATE>{rate:.2f}</RATE>
              <AMOUNT>{amount:.2f}</AMOUNT>
            </ALLINVENTORYENTRIES.LIST>
        """)

    total = parsed.get("total") or 0
    taxable_value = parsed.get("subtotal") or sum(li.get("amount", 0) for li in parsed.get("line_items", []))
    
    # Extract tax amounts
    taxes = parsed.get("taxes", [])
    cgst = sum(t.get("amount", 0) for t in taxes if t.get("type") == "CGST")
    sgst = sum(t.get("amount", 0) for t in taxes if t.get("type") == "SGST")
    igst = sum(t.get("amount", 0) for t in taxes if t.get("type") == "IGST")
    
    # If no taxes in taxes array, try to extract from register entry format
    if not cgst and not sgst and not igst:
        cgst = parsed.get("cgst", 0)
        sgst = parsed.get("sgst", 0)
        igst = parsed.get("igst", 0)
    
    # Determine voucher type name (default to voucher_type)
    voucher_type_name = voucher_type
    
    # Build ledger entries based on voucher type
    ledger_entries = []
    
    if voucher_type == "Purchase":
        # Purchase voucher structure:
        # Debit: Purchase (taxable value)
        # Debit: Input CGST (if applicable)
        # Debit: Input SGST (if applicable)
        # Debit: Input IGST (if applicable)
        # Credit: Supplier (party ledger, negative amount)
        
        # Purchase debit
        ledger_entries.append(f"""
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Purchase</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{taxable_value:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")
        
        # Input CGST debit (if applicable)
        if cgst > 0:
            ledger_entries.append(f"""
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Input CGST</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{cgst:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")
        
        # Input SGST debit (if applicable)
        if sgst > 0:
            ledger_entries.append(f"""
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Input SGST</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{sgst:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")
        
        # Input IGST debit (if applicable)
        if igst > 0:
            ledger_entries.append(f"""
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Input IGST</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{igst:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")
        
        # Supplier credit (party ledger)
        ledger_entries.append(f"""
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{party_name}</LEDGERNAME>
              <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-{total:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")
    else:
        # Sales voucher structure (default)
        # Debit: Customer (party ledger)
        # Credit: Sales (taxable value)
        # Credit: Output CGST (if applicable)
        # Credit: Output SGST (if applicable)
        # Credit: Output IGST (if applicable)
        
        # Customer debit (party ledger)
        ledger_entries.append(f"""
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{party_name}</LEDGERNAME>
              <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{total:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")
        
        # Sales credit
        ledger_entries.append(f"""
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Sales</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-{taxable_value:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")
        
        # Output CGST credit (if applicable)
        if cgst > 0:
            ledger_entries.append(f"""
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Output CGST</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-{cgst:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")
        
        # Output SGST credit (if applicable)
        if sgst > 0:
            ledger_entries.append(f"""
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Output SGST</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-{sgst:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")
        
        # Output IGST credit (if applicable)
        if igst > 0:
            ledger_entries.append(f"""
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Output IGST</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-{igst:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")
    
    # Validation: Ensure ledger entries balance (sum to 0)
    # Calculate sum of all ledger amounts
    ledger_sum = 0.0
    for entry in ledger_entries:
        # Extract amount from ledger entry string
        if "<AMOUNT>" in entry:
            try:
                amount_str = entry.split("<AMOUNT>")[1].split("</AMOUNT>")[0]
                amount = float(amount_str)
                ledger_sum += amount
            except (ValueError, IndexError):
                pass
    
    # Validate: Ledger entries should sum to 0 (balanced)
    if abs(ledger_sum) > 0.01:  # Allow small floating point differences
        logging.warning(f"⚠️  Ledger entries do not balance! Sum: {ledger_sum:.2f} (should be 0.00)")
        logging.warning(f"   Invoice: {inv_no}, Total: {total:.2f}, Taxable: {taxable_value:.2f}")
        logging.warning(f"   CGST: {cgst:.2f}, SGST: {sgst:.2f}, IGST: {igst:.2f}")
    
    # Validate: Item amounts vs purchase + tax should reconcile
    item_total = sum(li.get("amount", 0) for li in parsed.get("line_items", []))
    expected_total = taxable_value + cgst + sgst + igst
    if abs(item_total - taxable_value) > 0.01:
        logging.warning(f"⚠️  Item total ({item_total:.2f}) doesn't match taxable value ({taxable_value:.2f})")
    if abs(expected_total - total) > 0.01:
        logging.warning(f"⚠️  Expected total ({expected_total:.2f}) doesn't match actual total ({total:.2f})")
    
    # GST Consistency Checks
    if taxable_value > 0:
        # Check CGST percentage (should be ~9% for 18% GST split)
        if cgst > 0:
            cgst_percent = (cgst / taxable_value) * 100
            if abs(cgst_percent - 9.0) > 0.5:  # Allow 0.5% tolerance
                logging.warning(f"⚠️  CGST percentage is {cgst_percent:.2f}% (expected ~9% for 18% GST split)")
        
        # Check SGST percentage (should be ~9% for 18% GST split)
        if sgst > 0:
            sgst_percent = (sgst / taxable_value) * 100
            if abs(sgst_percent - 9.0) > 0.5:  # Allow 0.5% tolerance
                logging.warning(f"⚠️  SGST percentage is {sgst_percent:.2f}% (expected ~9% for 18% GST split)")
        
        # Check IGST percentage (should be ~18% if using IGST)
        if igst > 0:
            igst_percent = (igst / taxable_value) * 100
            if abs(igst_percent - 18.0) > 0.5:  # Allow 0.5% tolerance
                logging.warning(f"⚠️  IGST percentage is {igst_percent:.2f}% (expected ~18%)")
        
        # Check if both CGST+SGST and IGST are present (shouldn't happen)
        if (cgst > 0 or sgst > 0) and igst > 0:
            logging.warning(f"⚠️  Both CGST/SGST ({cgst:.2f}/{sgst:.2f}) and IGST ({igst:.2f}) are present - should use one or the other")
        
        # Validate base + tax = total
        calculated_total = taxable_value + cgst + sgst + igst
        if abs(calculated_total - total) > 0.01:
            logging.warning(f"⚠️  Base ({taxable_value:.2f}) + Tax ({cgst + sgst + igst:.2f}) = {calculated_total:.2f}, but total is {total:.2f}")
        else:
            logging.info(f"✅ GST validation passed: Base ({taxable_value:.2f}) + Tax ({cgst + sgst + igst:.2f}) = Total ({total:.2f})")
        
        # GST Type Selection Logic Validation (CGST+SGST vs IGST based on state codes)
        if company_state_code and gstin_raw:
            supplier_state_code = _extract_state_code(gstin_raw)
            if supplier_state_code:
                if company_state_code == supplier_state_code:
                    # Same state - should use CGST + SGST
                    if igst > 0:
                        logging.warning(f"⚠️  GST Type Mismatch: Company state ({company_state_code}) = Supplier state ({supplier_state_code}) → Should use CGST+SGST, but IGST is present")
                    if cgst == 0 and sgst == 0 and igst == 0:
                        logging.warning(f"⚠️  GST Type Mismatch: Same state transaction but no taxes found")
                else:
                    # Different state - should use IGST
                    if cgst > 0 or sgst > 0:
                        logging.warning(f"⚠️  GST Type Mismatch: Company state ({company_state_code}) ≠ Supplier state ({supplier_state_code}) → Should use IGST, but CGST/SGST are present")
                    if igst == 0 and (cgst == 0 and sgst == 0):
                        logging.warning(f"⚠️  GST Type Mismatch: Inter-state transaction but no IGST found")
    
    # Validate Sign Conventions
    # For Purchase: Debits positive (ISDEEMEDPOSITIVE=No), Credits negative (ISDEEMEDPOSITIVE=Yes)
    # For Sales: Debits positive (ISDEEMEDPOSITIVE=No), Credits negative (ISDEEMEDPOSITIVE=Yes)
    for entry in ledger_entries:
        if "<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>" in entry:
            # Debit - should be positive
            if "<AMOUNT>-" in entry:
                logging.warning(f"⚠️  Sign Convention Error: Debit entry has negative amount (should be positive)")
        elif "<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>" in entry:
            # Credit - should be negative
            if "<AMOUNT>" in entry and not "<AMOUNT>-" in entry:
                amount_match = entry.split("<AMOUNT>")[1].split("</AMOUNT>")[0] if "<AMOUNT>" in entry else ""
                try:
                    if float(amount_match) > 0:
                        logging.warning(f"⚠️  Sign Convention Error: Credit entry has positive amount (should be negative)")
                except:
                    pass
    
    # Validate Required Voucher Tags
    required_tags = ["DATE", "VOUCHERTYPENAME", "VCHTYPE", "VOUCHERNUMBER", "PARTYLEDGERNAME"]
    missing_tags = []
    # We'll check these after XML is generated
    
    body = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER VCHTYPE="{voucher_type}" ACTION="Create">
            <DATE>{formatted_date}</DATE>
            <EFFECTIVEDATE>{formatted_date}</EFFECTIVEDATE>
            <VOUCHERTYPENAME>{voucher_type_name}</VOUCHERTYPENAME>
            <VOUCHERNUMBER>{escape(str(inv_no or ""))}</VOUCHERNUMBER>
            <ISINVOICE>Yes</ISINVOICE>
            <PARTYLEDGERNAME>{party_name}</PARTYLEDGERNAME>
            <PARTYNAME>{party_name}</PARTYNAME>
            <PARTYGSTIN>{gstin}</PARTYGSTIN>
            {''.join(stock_items)}
            {''.join(ledger_entries)}
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""
    
    # Validate Required Voucher Tags exist in generated XML
    for tag in required_tags:
        if f"<{tag}>" not in body:
            logging.error(f"❌ Missing required tag: <{tag}>")
    
    # Validate EFFECTIVEDATE, PARTYGSTIN, ISINVOICE (optional but recommended)
    recommended_tags = ["EFFECTIVEDATE", "PARTYGSTIN", "ISINVOICE"]
    for tag in recommended_tags:
        if f"<{tag}>" not in body:
            logging.warning(f"⚠️  Missing recommended tag: <{tag}>")
    
    return body
