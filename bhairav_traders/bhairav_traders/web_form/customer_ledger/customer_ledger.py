import frappe
from bhairav_traders.portal_utils import update_website_context, get_current_customer

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/customer-ledger"
        raise frappe.Redirect
    update_website_context(context)

def get_list_context(context):
    update_website_context(context)
    context.no_cache = 1
    context.get_list = get_customer_ledger_entries

def get_customer_ledger_entries(doctype, txt=None, filters=None, limit_start=0, limit_page_length=20, order_by="creation desc", **kwargs):
    customer = get_current_customer()
    
    if not customer:
        return []
        
    entries = frappe.get_all(
        "Customer Ledger",
        filters={"customer": customer},
        fields=["name", "posting_date", "voucher_type", "voucher_no", "debit", "credit", "against", "balance"],
        order_by="posting_date desc, creation desc",
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        ignore_permissions=True
    )
    
    for entry in entries:
        if entry.voucher_type == "Sales Invoice":
            is_return = frappe.db.get_value("Sales Invoice", entry.voucher_no, "is_return")
            if is_return:
                entry.voucher_type = "Sales Return"
        elif entry.voucher_type == "Payment Entry":
            payment_type = frappe.db.get_value("Payment Entry", entry.voucher_no, "payment_type")
            if payment_type == "Pay":
                entry.voucher_type = "Refund"
                
    return entries

def flt(val):
    try:
        return float(val or 0)
    except Exception:
        return 0.0
