import frappe
from frappe import _
from bhairav_traders.credit_limit import check_account_lock_status
from bhairav_traders.portal_utils import update_website_context, get_current_customer

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/customer-order"
        raise frappe.Redirect
        
    update_website_context(context)
    customer = get_current_customer()
    
    if customer and hasattr(context, "doc") and context.doc:
        context.doc.customer = customer
        
    if customer and check_account_lock_status(customer):
        lock_reason = frappe.db.get_value("Customer", customer, "lock_reason")
        frappe.msgprint(_("Warning: Your account is currently locked due to overdue payments. Reason: {0}").format(lock_reason))

def get_list_context(context):
    update_website_context(context)
    context.get_list = get_customer_orders

def get_customer_orders(doctype, txt=None, filters=None, limit_start=0, limit_page_length=20, order_by="creation desc", **kwargs):
    customer = get_current_customer()
    
    if not customer:
        return []
        
    return frappe.get_all(
        "Sales Order",
        filters={"customer": customer},
        fields=["name", "transaction_date", "grand_total", "status", "customer_approval_status"],
        order_by="creation desc",
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        ignore_permissions=True
    )
