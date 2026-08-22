import frappe
from frappe import _
from frappe.utils import flt
from bhairav_traders.portal_utils import get_current_customer, update_website_context
from bhairav_traders.credit_limit import check_account_lock_status

login_required = 1
no_cache = 1

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/portal"
        raise frappe.Redirect

    # Ensure website context is loaded for sidebar, menu etc
    update_website_context(context)
    context.show_sidebar = 1

    customer = get_current_customer()
    if not customer:
        context.customer = None
        context.error = _("No customer account linked to this user profile. Please contact the administrator.")
        return

    context.customer = customer
    customer_doc = frappe.get_doc("Customer", customer)
    context.customer_name = customer_doc.customer_name

    # Check lock status
    is_locked, max_overdue_days = check_account_lock_status(customer)
    context.is_locked = is_locked
    context.lock_reason = customer_doc.lock_reason

    # Get credit limit
    company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")
    
    credit_limit = frappe.db.get_value(
        "Customer Credit Limit",
        {"parent": customer, "company": company},
        "credit_limit"
    ) or 0.0
    context.credit_limit = flt(credit_limit)

    # Get outstanding invoices balance
    outstanding_balance = frappe.db.sql("""
        SELECT SUM(outstanding_amount)
        FROM `tabSales Invoice`
        WHERE customer = %s AND docstatus = 1 AND outstanding_amount > 0
    """, (customer,))[0][0] or 0.0
    context.outstanding_balance = flt(outstanding_balance)

    # Get remaining credit
    if context.credit_limit > 0:
        context.remaining_credit = max(0.0, context.credit_limit - context.outstanding_balance)
    else:
        context.remaining_credit = 0.0

    # Get pending approvals count
    context.pending_approvals_count = frappe.db.count("Sales Order", filters={
        "customer": customer,
        "customer_approval_status": "Pending",
        "docstatus": 0
    })

    # Get total orders count
    context.total_orders_count = frappe.db.count("Sales Order", filters={
        "customer": customer
    })

    # Fetch recent orders (last 5)
    recent_orders = frappe.get_all(
        "Sales Order",
        filters={"customer": customer},
        fields=["name", "transaction_date", "grand_total", "status", "customer_approval_status", "per_billed"],
        order_by="creation desc",
        limit=5,
        ignore_permissions=True
    )
    
    for order in recent_orders:
        if order.per_billed and order.per_billed >= 100:
            outstanding = frappe.db.sql("""
                SELECT SUM(outstanding_amount) 
                FROM `tabSales Invoice` 
                WHERE name IN (SELECT parent FROM `tabSales Invoice Item` WHERE sales_order = %s) 
                AND docstatus = 1
            """, (order.name,))
            
            if outstanding and outstanding[0][0] is not None and outstanding[0][0] <= 0:
                order.status = "Completed"
            
    context.recent_orders = recent_orders

    # Fetch recent invoices (last 5)
    context.recent_invoices = frappe.get_all(
        "Sales Invoice",
        filters={"customer": customer},
        fields=["name", "posting_date", "grand_total", "outstanding_amount", "status"],
        order_by="creation desc",
        limit=5,
        ignore_permissions=True
    )
