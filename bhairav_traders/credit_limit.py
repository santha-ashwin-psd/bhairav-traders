import frappe
from frappe import _
from frappe.utils import flt, today, date_diff, getdate, add_days

def is_salesman_user(user):
    if not user or user == "Guest":
        return False
    if user == "Administrator":
        return True
    user_roles = frappe.get_roles(user)
    sales_roles = {"Salesman", "Sales User", "System Manager", "Accounts Manager", "Director"}
    return bool(sales_roles.intersection(user_roles))

def check_account_lock_status(customer_name):
    """
    Checks if customer has unpaid invoices exceeding credit_days_allowed (default 60 days).
    If overdue > credit_days_allowed, locks customer account.
    If all overdue invoices are settled, unlocks account automatically.
    """
    if not customer_name:
        return False
        
    customer = frappe.get_doc("Customer", customer_name)
    credit_days = flt(getattr(customer, "credit_days_allowed", 60)) or 60
    
    # Fetch unpaid/partially paid sales invoices for this customer
    overdue_invoices = frappe.db.sql("""
        SELECT name, posting_date, due_date, outstanding_amount
        FROM `tabSales Invoice`
        WHERE customer = %s
          AND docstatus = 1
          AND outstanding_amount > 0
        ORDER BY posting_date ASC
    """, (customer_name,), as_dict=True)
    
    today_date = getdate(today())
    is_locked = False
    lock_reasons = []
    
    for inv in overdue_invoices:
        days_old = date_diff(today_date, inv.posting_date)
        if days_old > credit_days:
            is_locked = True
            lock_reasons.append(f"Invoice {inv.name} ({inv.posting_date}) is unpaid beyond {credit_days} days (Age: {days_old} days, Outstanding: ₹{inv.outstanding_amount:,.2f})")
            
    if is_locked:
        reason_str = " | ".join(lock_reasons[:3])
        if getattr(customer, "is_account_locked", 0) != 1 or getattr(customer, "lock_reason", "") != reason_str:
            frappe.db.set_value("Customer", customer_name, {
                "is_account_locked": 1,
                "lock_reason": reason_str
            })
    else:
        if getattr(customer, "is_account_locked", 0) == 1:
            frappe.db.set_value("Customer", customer_name, {
                "is_account_locked": 0,
                "lock_reason": ""
            })
            
    return is_locked


def validate_sales_order_credit(doc, method=None):
    """
    Validates Credit Limit and Salesman Order Approval rules on Sales Order:
    1. Salesman Order Placing: If placed by salesman, mark as Pending Customer Approval.
    2. Condition 1: If no credit limit is issued (or 0), order requires advance payment.
    3. Condition 2: If credit limit is issued, total outstanding + SO total must be within limit.
    4. Account Locking: If customer account is locked, block SO creation.
    """
    if not doc.customer:
        return

    # Auto-populate delivery_date and rate on child items if missing
    if doc.items:
        for item in doc.items:
            if not getattr(item, "delivery_date", None):
                item.delivery_date = doc.delivery_date or add_days(today(), 7)
            if (not getattr(item, "rate", None) or flt(item.rate) <= 0) and getattr(item, "item_code", None):
                std_rate = frappe.db.get_value("Item Price", {"item_code": item.item_code, "selling": 1}, "price_list_rate") or frappe.db.get_value("Item", item.item_code, "standard_rate") or 0
                item.rate = flt(std_rate)
            if getattr(item, "qty", None) and getattr(item, "rate", None):
                item.amount = flt(item.qty) * flt(item.rate)
        
    # Check if placed by salesman (only on first creation)
    if doc.is_new() and is_salesman_user(frappe.session.user):
        doc.placed_by_salesman = 1
        if not doc.customer_approval_status or doc.customer_approval_status == "Not Required":
            doc.customer_approval_status = "Pending"

    # Check and update account lock status
    is_locked = check_account_lock_status(doc.customer)
    customer_doc = frappe.get_doc("Customer", doc.customer)
    
    if is_locked:
        frappe.throw(
            _("Customer account '{0}' is locked due to overdue payments. Reason: {1}").format(
                doc.customer, customer_doc.lock_reason
            )
        )
        
    # Check customer credit limits
    credit_limit = frappe.db.get_value(
        "Customer Credit Limit",
        {"parent": doc.customer, "company": doc.company},
        "credit_limit"
    ) or 0
    
    credit_limit = flt(credit_limit)
    
    if credit_limit <= 0:
        # Condition 1: No credit limit -> Advance Payment Required
        doc.requires_advance_payment = 1
        frappe.msgprint(
            _("Notice: No credit limit is issued for customer '{0}'. Order will be executed on advance payment.").format(doc.customer)
        )
    else:
        doc.requires_advance_payment = 0
        # Condition 2: Check total exposure against credit limit
        total_outstanding = frappe.db.sql("""
            SELECT SUM(outstanding_amount)
            FROM `tabSales Invoice`
            WHERE customer = %s AND docstatus = 1
        """, (doc.customer,))[0][0] or 0.0
        
        grand_total = flt(doc.grand_total)
        total_exposure = flt(total_outstanding) + grand_total
        
        if total_exposure > credit_limit:
            frappe.throw(
                _("Credit Limit Exceeded for '{0}'. Credit Limit: ₹{1:,.2f}, Outstanding + New Order: ₹{2:,.2f}").format(
                    doc.customer, credit_limit, total_exposure
                )
            )


def validate_sales_invoice_locking(doc, method=None):
    """
    Validates account lock and customer approval on Sales Invoice submission:
    1. If Sales Order was placed by Salesman, verify Customer Approval status is 'Approved'.
    2. Invoicing for locked accounts is blocked unless approved_during_lock is checked by Accounts Manager/Director.
    """
    if not doc.customer:
        return
        
    # Check linked Sales Orders for customer approval
    if doc.items:
        for item in doc.items:
            so_name = getattr(item, "sales_order", None)
            if so_name:
                so_doc = frappe.get_doc("Sales Order", so_name)
                if getattr(so_doc, "placed_by_salesman", 0) and getattr(so_doc, "customer_approval_status", "") != "Approved":
                    frappe.throw(
                        _("Sales Order {0} is placed by Salesman and is currently '{1}'. Invoicing is blocked until Customer approves the order on the Portal.").format(
                            so_name, getattr(so_doc, "customer_approval_status", "Pending")
                        )
                    )

    is_locked = check_account_lock_status(doc.customer)
    
    if is_locked:
        if doc.approved_during_lock:
            # Check permission: User must have System Manager, Accounts Manager, or Director role
            user_roles = frappe.get_roles(frappe.session.user)
            if "Accounts Manager" not in user_roles and "System Manager" not in user_roles and "Director" not in user_roles:
                frappe.throw(_("Only Accounts Manager or Director is authorized to approve invoicing for locked accounts."))
        else:
            customer_doc = frappe.get_doc("Customer", doc.customer)
            frappe.throw(
                _("Invoicing is blocked because Customer '{0}' account is locked due to overdue payments beyond allowed credit days. Reason: {1}").format(
                    doc.customer, customer_doc.lock_reason
                )
            )


def validate_advance_payment(doc, method=None):
    """
    Called before_submit on Sales Invoice or Delivery Note:
    If Sales Order required advance payment, verify that advance payment has been submitted.
    """
    if not doc.items:
        return
        
    for item in doc.items:
        so_name = getattr(item, "sales_order", None)
        if so_name:
            requires_adv = frappe.db.get_value("Sales Order", so_name, "requires_advance_payment")
            if requires_adv:
                advance_paid = frappe.db.get_value("Sales Order", so_name, "advance_paid") or 0
                so_grand_total = frappe.db.get_value("Sales Order", so_name, "grand_total") or 0
                if flt(advance_paid) < flt(so_grand_total):
                    frappe.throw(_("Sales Order {0} requires 100% advance payment before invoicing. Paid: ₹{1:,.2f}, Order Total: ₹{2:,.2f}").format(
                        so_name, flt(advance_paid), flt(so_grand_total)
                    ))


def sync_all_customer_lock_statuses():
    """
    Daily scheduled cron task: Recalculate lock status for all active customers.
    """
    customers = frappe.get_all("Customer", filters={"disabled": 0}, pluck="name")
    for cust in customers:
        try:
            check_account_lock_status(cust)
        except Exception as e:
            frappe.log_error(f"Error syncing account lock for customer {cust}: {e}")

def set_workflow_state(doc, state):
    """Helper to set ERPNext workflow state on a Sales Order."""
    frappe.db.set_value("Sales Order", doc.name, "workflow_state", state)
    doc.workflow_state = state

    is_salesman = is_salesman_user(frappe.session.user)
    
    if is_salesman:
        doc.placed_by_salesman = 1
        doc.customer_approval_status = "Pending"
    else:
        doc.customer_approval_status = "Not Required"

def after_insert_sales_order(doc, method=None):
    """
    Handle workflow jumps after the document is inserted in Draft state.
    Frappe blocks setting workflow_state directly during creation (insert),
    so we must bypass it immediately after insertion via set_value.
    """
    is_salesman = is_salesman_user(frappe.session.user)
    
    if is_salesman:
        frappe.db.set_value("Sales Order", doc.name, "workflow_state", "Pending Customer Approval")
    else:
        frappe.db.set_value("Sales Order", doc.name, "workflow_state", "To Be Processed")