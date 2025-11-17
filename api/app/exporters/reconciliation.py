"""CSV exporters for reconciliation data"""
import csv
from io import StringIO
from typing import Dict, Any, List, Optional


def export_missing_invoices_csv(
    missing_invoices: List[Dict[str, Any]], 
    source: str = "sales_register"
) -> str:
    """Export missing invoices to CSV format.
    
    Args:
        missing_invoices: List of invoice dictionaries
        source: Source document type (sales_register, gstr1, etc.)
    """
    buf = StringIO()
    writer = csv.writer(buf)
    
    # Header
    writer.writerow([
        "Invoice Number",
        "Invoice Date", 
        "Customer Name",
        "Customer GSTIN",
        "Taxable Value",
        "Total Value"
    ])
    
    # Data rows
    for inv in missing_invoices:
        inv_no = inv.get("invoice_number")
        if isinstance(inv_no, dict):
            inv_no = inv_no.get("value", "")
        
        inv_date = inv.get("invoice_date") or inv.get("date", "")
        if isinstance(inv_date, dict):
            inv_date = inv_date.get("value", "")
        
        customer_name = inv.get("customer_name", "")
        customer_gstin = inv.get("customer_gstin", "")
        taxable_value = inv.get("taxable_value", 0)
        total_value = inv.get("total_value") or inv.get("total", 0)
        
        writer.writerow([
            inv_no or "",
            inv_date or "",
            customer_name or "",
            customer_gstin or "",
            taxable_value or 0,
            total_value or 0
        ])
    
    return buf.getvalue()


def export_value_mismatches_csv(
    value_mismatches: List[Dict[str, Any]]
) -> str:
    """Export value mismatches to CSV format."""
    buf = StringIO()
    writer = csv.writer(buf)
    
    # Header
    writer.writerow([
        "Invoice Number",
        "Invoice Date",
        "Sales Register Taxable Value",
        "Sales Register Total",
        "GSTR-1 Taxable Value", 
        "GSTR-1 Total",
        "Taxable Value Difference",
        "Total Difference"
    ])
    
    # Data rows
    for mismatch in value_mismatches:
        inv_no = mismatch.get("invoice_number")
        if isinstance(inv_no, dict):
            inv_no = inv_no.get("value", "")
        
        inv_date = mismatch.get("invoice_date") or mismatch.get("date", "")
        if isinstance(inv_date, dict):
            inv_date = inv_date.get("value", "")
        
        sr_data = mismatch.get("sales_register", {})
        g1_data = mismatch.get("gstr1", {})
        diff_data = mismatch.get("difference", {})
        
        writer.writerow([
            inv_no or "",
            inv_date or "",
            sr_data.get("taxable_value", 0),
            sr_data.get("total", 0),
            g1_data.get("taxable_value", 0),
            g1_data.get("total", 0),
            diff_data.get("taxable_value", 0),
            diff_data.get("total", 0)
        ])
    
    return buf.getvalue()


def export_itc_mismatch_summary_csv(
    recon: Dict[str, Any]
) -> str:
    """Export ITC mismatch summary to CSV format for Purchase Register vs GSTR-3B."""
    buf = StringIO()
    writer = csv.writer(buf)
    
    # Header
    writer.writerow([
        "Category",
        "Purchase Register",
        "GSTR-3B",
        "Difference",
        "Status"
    ])
    
    totals = recon.get("totals", {})
    pr_totals = totals.get("purchase_register", {})
    g3b_totals = totals.get("gstr3b", {})
    diff = recon.get("difference", {})
    status = recon.get("status", "unknown")
    
    # Summary rows
    writer.writerow([
        "IGST",
        pr_totals.get("igst", 0),
        g3b_totals.get("igst", 0),
        diff.get("igst", 0),
        "Overclaimed" if status == "itc_overclaimed" else "Underclaimed" if status == "itc_underclaimed" else "Matched"
    ])
    
    writer.writerow([
        "CGST",
        pr_totals.get("cgst", 0),
        g3b_totals.get("cgst", 0),
        diff.get("cgst", 0),
        ""
    ])
    
    writer.writerow([
        "SGST",
        pr_totals.get("sgst", 0),
        g3b_totals.get("sgst", 0),
        diff.get("sgst", 0),
        ""
    ])
    
    writer.writerow([
        "Total ITC",
        pr_totals.get("total", 0),
        g3b_totals.get("total", 0),
        diff.get("total", 0),
        status
    ])
    
    return buf.getvalue()

