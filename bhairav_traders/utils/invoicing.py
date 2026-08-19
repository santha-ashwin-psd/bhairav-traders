import frappe

def validate_eway_bill(doc, method=None):
    """
    Ensure E-Way Bill No is provided for Sales Invoices over ₹50,000.
    """
    if doc.grand_total > 50000:
        if not doc.get("e_way_bill_no"):
            frappe.throw("An E-Way Bill No is mandatory for invoices exceeding ₹50,000 as per GST compliance rules.")
