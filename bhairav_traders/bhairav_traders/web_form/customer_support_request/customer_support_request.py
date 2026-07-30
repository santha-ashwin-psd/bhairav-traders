import frappe
from bhairav_traders.portal_utils import update_website_context, get_current_customer

def get_context(context):
    update_website_context(context)
    context.parents = [{"title": "Support", "route": "/customer-support-request"}]

def get_list_context(context):
    update_website_context(context)
    context.get_list = get_support_requests

def get_support_requests(doctype, txt=None, filters=None, limit_start=0, limit_page_length=20, order_by="creation desc", **kwargs):
    customer = get_current_customer()
    
    if not customer:
        return []
        
    return frappe.get_all(
        "Customer Support Request",
        filters={"customer": customer},
        fields=["name", "subject", "category", "priority", "status", "creation", "description"],
        order_by="creation desc",
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        ignore_permissions=True
    )
