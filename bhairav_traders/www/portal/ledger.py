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
        frappe.local.flags.redirect_location = "/login?redirect-to=/portal/ledger"
        raise frappe.Redirect
        
    customer = get_current_customer()
    context.customer = customer
    
    if customer:
        entries = frappe.db.sql("""
            SELECT
                posting_date,
                voucher_type,
                voucher_no,
                debit,
                credit,
                against
            FROM `tabGL Entry`
            WHERE party_type = 'Customer' AND party = %s AND is_cancelled = 0
            ORDER BY posting_date ASC, creation ASC
        """, (customer,), as_dict=True)
        
        balance = 0.0
        for entry in entries:
            balance += (entry.debit - entry.credit)
            entry.balance = balance
            
        context.entries = entries
        context.total_balance = balance
    else:
        context.entries = []
        context.total_balance = 0.0
