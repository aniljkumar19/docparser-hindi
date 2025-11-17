def invoice_to_tally_xml(parse_result: dict) -> str:
    """Convert ParseResult dict into a minimal Tally XML voucher.
    This is a stub; map fields according to your Tally config.
    """
    inv = parse_result
    inv_no = inv.get("invoice_number",{}).get("value") or "INV-UNKNOWN"
    date = inv.get("date",{}).get("value") or "2025-01-01"
    total = inv.get("total") or 0

    xml = f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF='TallyUDF'>
          <VOUCHER VCHTYPE='Sales' ACTION='Create'>
            <VOUCHERNUMBER>{inv_no}</VOUCHERNUMBER>
            <DATE>{date.replace('-','')}</DATE>
            <PARTYLEDGERNAME>{(inv.get('buyer') or {}).get('name') or 'Buyer'}</PARTYLEDGERNAME>
            <BASICBASEPARTYNAME>{(inv.get('buyer') or {}).get('name') or 'Buyer'}</BASICBASEPARTYNAME>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Sales</LEDGERNAME>
              <AMOUNT>{total}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""
    return xml
