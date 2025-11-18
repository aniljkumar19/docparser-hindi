from typing import Dict, Any
from xml.sax.saxutils import escape

def _format_tally_date(date_str: str) -> str:
    """Convert date from YYYY-MM-DD to YYYYMMDD format for Tally"""
    if not date_str:
        return ""
    # Remove hyphens and any time portion
    date_str = str(date_str).strip()
    if "T" in date_str:
        date_str = date_str.split("T")[0]
    return date_str.replace("-", "")

def invoice_to_tally_xml(parsed: Dict[str, Any], voucher_type: str = "Sales") -> str:
    """
    Generate Tally XML for a single invoice/voucher.
    
    Args:
        parsed: Parsed invoice/register entry data
        voucher_type: "Sales" or "Purchase" - determines voucher type and ledger structure
    """
    inv_no = (parsed.get("invoice_number") or {}).get("value") if isinstance(parsed.get("invoice_number"), dict) else parsed.get("invoice_number")
    date = (parsed.get("date") or {}).get("value") if isinstance(parsed.get("date"), dict) else parsed.get("date")
    buyer = parsed.get("buyer") or {}
    party_name = escape(str(buyer.get("name") or "Buyer"))
    gstin = escape(str(buyer.get("gstin") or ""))
    
    # Format date for Tally (YYYYMMDD)
    formatted_date = _format_tally_date(date or "")

    stock_items = []
    for li in parsed.get("line_items", []):
        desc = escape(str(li.get("desc", "Item")))
        qty = li.get("qty", 0)
        rate = li.get("unit_price", 0)
        amount = li.get("amount", 0)
        stock_items.append(f"""
            <ALLINVENTORYENTRIES.LIST>
              <STOCKITEMNAME>{desc}</STOCKITEMNAME>
              <RATE>{rate}</RATE>
              <AMOUNT>{amount}</AMOUNT>
              <ACTUALQTY>{qty}</ACTUALQTY>
              <BILLEDQTY>{qty}</BILLEDQTY>
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
            <VOUCHERTYPENAME>{voucher_type_name}</VOUCHERTYPENAME>
            <VOUCHERNUMBER>{escape(str(inv_no or ""))}</VOUCHERNUMBER>
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
    return body
