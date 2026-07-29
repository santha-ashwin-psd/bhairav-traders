import frappe
from bhairav_traders.portal_utils import update_website_context, get_current_customer

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/customer-invoice"
        raise frappe.Redirect
    update_website_context(context)

def get_list_context(context):
    update_website_context(context)
    context.get_list = get_customer_invoices

def get_customer_invoices(doctype, txt=None, filters=None, limit_start=0, limit_page_length=20, order_by="posting_date desc", **kwargs):
    customer = get_current_customer()
    
    if not customer:
        return []
        
    return frappe.get_all(
        "Sales Invoice",
        filters={"customer": customer, "docstatus": 1},
        fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "status"],
        order_by="posting_date desc",
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        ignore_permissions=True
    )
