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
            
    # Prevent manual modification of these fields by non-admins
    if not doc.is_new():
        old_doc = doc.get_doc_before_save()
        if old_doc:
            if old_doc.placed_by_salesman != doc.placed_by_salesman or old_doc.customer_approval_status != doc.customer_approval_status:
                roles = frappe.get_roles(frappe.session.user)
                if frappe.session.user != "Administrator" and "System Manager" not in roles and "Customer" not in roles:
                    frappe.throw(_("Only Administrators or the Customer (via portal) can modify 'Placed By Salesman' or 'Customer Approval Status'."))

    # Check and update account lock status
    is_locked = check_account_lock_status(doc.customer)
    customer_doc = frappe.get_doc("Customer", doc.customer)
    
    is_breached = False
    breach_reason = []

    if is_locked and doc.is_new():
        is_breached = True
        breach_reason.append(f"Account locked: {customer_doc.lock_reason}")
        
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
        
        doc.credit_exposure = total_exposure
        doc.available_credit = credit_limit - total_exposure if credit_limit > total_exposure else 0.0
        
        if total_exposure > credit_limit:
            is_breached = True
            breach_reason.append(f"Limit: ₹{credit_limit:,.2f}, Total Exposure: ₹{total_exposure:,.2f}")

    if is_breached:
        doc.credit_limit_breached = 1
        doc.credit_breach_reason = " | ".join(breach_reason)[:140]
        if doc.workflow_state == "Pending Customer Approval":
            # State transitions to Pending Customer Approval ONLY when Commercial clicks "Credit Approve"
            frappe.throw(_("Credit Limit Exceeded! You must select 'Credit Hold'. Total Exposure: ₹{0:,.2f} exceeds Limit: ₹{1:,.2f}").format(total_exposure, credit_limit))
    else:
        doc.credit_limit_breached = 0
        doc.credit_breach_reason = ""
        
    # Map Workflow State to Credit Check Status
    if doc.workflow_state == "Credit Hold":
        doc.credit_check_status = "Credit Hold"
    elif doc.workflow_state in ["Pending Customer Approval", "Customer Approved", "Ready for Picking", "Packed", "Ready for Dispatch", "Dispatched", "Invoiced", "Completed"]:
        doc.credit_check_status = "Approved"
    elif doc.workflow_state in ["Draft", "Pending Sales Manager Approval", "Pending Regional Manager Approval", "Pending Sales Head Approval", "Pending Director Approval", "Pending Commercial Credit Check"]:
        doc.credit_check_status = "Pending"



def validate_sales_invoice_locking(doc, method=None):
    """
    Validates account lock and customer approval on Sales Invoice submission:
    1. If Sales Order was placed by Salesman, verify Customer Approval status is 'Approved'.
    2. Invoicing for locked accounts is blocked unless approved_during_lock is checked by Accounts Manager/Director.
    """
    if not doc.customer:
        return
        
    if getattr(doc, "is_return", 0):
        user_roles = frappe.get_roles(frappe.session.user)
        if "Accounts Manager" not in user_roles and "Finance Manager" not in user_roles and "System Manager" not in user_roles and "Director" not in user_roles:
            frappe.throw(_("Only the Finance Manager (Accounts Manager) or Director is authorized to approve and submit Sales Returns."))
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
            if "Accounts Manager" not in user_roles and "Finance Manager" not in user_roles and "System Manager" not in user_roles and "Director" not in user_roles:
                frappe.throw(_("Only the Finance Manager or Director is authorized to approve invoicing for locked accounts."))
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
    pass
def sales_invoice_on_submit(doc, method=None):
    """
    Called on_submit of Sales Invoice.
    Automatically marks linked Sales Orders as 'Completed' in the Workflow
    if they are 100% billed.
    """
    if not doc.items:
        return
        
    so_names = set(item.sales_order for item in doc.items if getattr(item, "sales_order", None))
    
    for so_name in so_names:
        per_billed = frappe.db.get_value("Sales Order", so_name, "per_billed") or 0
        if flt(per_billed) >= 100.0:
            current_state = frappe.db.get_value("Sales Order", so_name, "workflow_state")
            if current_state not in ["Invoiced", "Completed"]:
                frappe.db.set_value("Sales Order", so_name, "workflow_state", "Invoiced")
                so_doc = frappe.get_doc("Sales Order", so_name)
                so_doc.add_comment("Comment", text=f"Workflow state automatically marked as Invoiced because Sales Invoice {doc.name} fulfilled 100% billing.")

def set_permissions():
    """Run via bench execute bhairav_traders.credit_limit.set_permissions"""
    import frappe
    # For Sales Order
    doctype = "Sales Order"
    roles = ["Accounts Manager", "Accounts User"]
    
    for role in roles:
        # Check if permission exists
        perm = frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": role})
        if not perm:
            doc = frappe.get_doc({
                "doctype": "Custom DocPerm",
                "parent": doctype,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": role,
                "read": 1,
                "write": 0,
                "create": 0,
                "submit": 1,
                "cancel": 1,
                "amend": 1
            })
            doc.insert(ignore_permissions=True)
            print(f"Added Custom DocPerm for {role} on {doctype}")
        else:
            frappe.db.set_value("Custom DocPerm", perm, {
                "read": 1,
                "write": 0,
                "create": 0,
                "submit": 1,
                "cancel": 1,
                "amend": 1
            })
            print(f"Updated Custom DocPerm for {role} on {doctype}")
    
    frappe.clear_cache(doctype=doctype)
    print("Permissions updated successfully!")

@frappe.whitelist()
def get_customer_credit_details(customer, company):
    if not customer:
        return {"credit_limit": 0, "total_outstanding": 0}
        
    credit_limit = frappe.db.get_value(
        "Customer Credit Limit",
        {"parent": customer, "company": company},
        "credit_limit"
    ) or 0
    
    total_outstanding = frappe.db.sql("""
        SELECT SUM(outstanding_amount)
        FROM `tabSales Invoice`
        WHERE customer = %s AND docstatus = 1
    """, (customer,))[0][0] or 0.0
    
    return {
        "credit_limit": frappe.utils.flt(credit_limit),
        "total_outstanding": frappe.utils.flt(total_outstanding)
    }

def validate_so_completion(doc, method=None):
    """
    Blocks the 'Complete' workflow action on a Sales Order unless
    all linked Sales Invoices are fully paid (outstanding_amount = 0).
    """
    if doc.workflow_state != "Completed":
        return

    # Find all linked submitted Sales Invoices
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "customer": doc.customer,
        },
        fields=["name", "outstanding_amount", "grand_total"],
    )

    # Filter to only those linked to this Sales Order via Sales Invoice Item
    linked = frappe.db.sql("""
        SELECT DISTINCT si.name, si.outstanding_amount, si.grand_total
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE sii.sales_order = %s AND si.docstatus = 1
    """, (doc.name,), as_dict=True)

    if not linked:
        frappe.throw(_(
            "Cannot mark as Completed. No submitted Sales Invoice found linked to this Sales Order. "
            "Please create and submit a Sales Invoice first."
        ))

    unpaid = [inv for inv in linked if flt(inv.outstanding_amount) > 0]
    if unpaid:
        names = ", ".join([inv.name for inv in unpaid])
        frappe.throw(_(
            "Cannot mark as Completed. The following Sales Invoice(s) still have outstanding payments: "
            "<b>{0}</b>. Please collect payment before completing this order."
        ).format(names))
