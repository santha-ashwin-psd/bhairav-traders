import frappe
from frappe import _

login_required = 1

def get_current_customer():
    if frappe.session.user == "Guest":
        return None
    portal_user = frappe.db.get_value("Portal User", {"user": frappe.session.user}, "parent")
    if portal_user:
        return portal_user
    contact = frappe.db.get_value("Contact", {"email_id": frappe.session.user})
    if contact:
        customer = frappe.db.get_value("Dynamic Link", {"parent": contact, "link_doctype": "Customer"}, "link_name")
        if customer:
            return customer
    return frappe.db.get_value("Customer", {"email_id": frappe.session.user})

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/portal/support"
        raise frappe.Redirect
        
    customer = get_current_customer()
    context.customer = customer
    
    if customer:
        context.tickets = frappe.get_all(
            "Customer Support Request",
            filters={"customer": customer},
            fields=["name", "posting_date", "subject", "category", "priority", "status"],
            order_by="creation desc"
        )
    else:
        context.tickets = []
        
    context.web_form_url = "/customer-support-request/new"
