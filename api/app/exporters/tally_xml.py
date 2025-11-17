from typing import Dict, Any
from xml.sax.saxutils import escape

def invoice_to_tally_xml(parsed: Dict[str, Any]) -> str:
    inv_no = (parsed.get("invoice_number") or {}).get("value") if isinstance(parsed.get("invoice_number"), dict) else parsed.get("invoice_number")
    date = (parsed.get("date") or {}).get("value") if isinstance(parsed.get("date"), dict) else parsed.get("date")
    buyer = parsed.get("buyer") or {}
    party_name = escape(str(buyer.get("name") or "Buyer"))
    gstin = escape(str(buyer.get("gstin") or ""))

    stock_items = []
    for li in parsed.get("line_items", []):
        desc = escape(str(li.get("desc","Item")))
        qty = li.get("qty",0)
        rate = li.get("unit_price",0)
        amount = li.get("amount",0)
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
    body = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER VCHTYPE="Sales" ACTION="Create">
            <DATE>{escape(str(date or ""))}</DATE>
            <VOUCHERNUMBER>{escape(str(inv_no or ""))}</VOUCHERNUMBER>
            <PARTYNAME>{party_name}</PARTYNAME>
            <PARTYGSTIN>{gstin}</PARTYGSTIN>
            {''.join(stock_items)}
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Sales</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{total}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""
    return body
