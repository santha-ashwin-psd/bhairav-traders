import frappe
from bhairav_traders.portal_utils import update_website_context, get_current_customer

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/customer-ledger"
        raise frappe.Redirect
    update_website_context(context)

def get_list_context(context):
    update_website_context(context)
    context.get_list = get_customer_ledger_entries

def get_customer_ledger_entries(doctype, txt=None, filters=None, limit_start=0, limit_page_length=20, order_by="creation desc", **kwargs):
    customer = get_current_customer()
    
    if not customer:
        return []
        
    entries = frappe.db.sql("""
        SELECT
            name,
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
        balance += (flt(entry.debit) - flt(entry.credit))
        entry.balance = balance
        
    entries.reverse()
    
    start = int(limit_start or 0)
    page = int(limit_page_length or 20)
    return entries[start:start+page]

def flt(val):
    try:
        return float(val or 0)
    except Exception:
        return 0.0
