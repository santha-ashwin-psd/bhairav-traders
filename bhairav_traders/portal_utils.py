import frappe
import frappe.model.workflow

def get_current_customer():
    if frappe.session.user == "Guest":
        return None
    # ERPNext's Portal User (child of Customer DocType) - check this first
    portal_user = frappe.db.get_value("Portal User", {"user": frappe.session.user}, "parent")
    if portal_user:
        return portal_user
    # Fallback: Check contact linked to customer via Dynamic Link
    contact = frappe.db.get_value("Contact", {"email_id": frappe.session.user})
    if contact:
        customer = frappe.db.get_value("Dynamic Link", {"parent": contact, "link_doctype": "Customer"}, "link_name")
        if customer:
            # Auto-link via Portal User table so ERPNext's has_website_permission works
            _ensure_portal_user_linked(frappe.session.user, customer)
            return customer
    
    # Second fallback: Direct Customer email_id
    customer = frappe.db.get_value("Customer", {"email_id": frappe.session.user})
    if customer:
        _ensure_portal_user_linked(frappe.session.user, customer)
        return customer
        
    return None

def _ensure_portal_user_linked(user_email, customer):
    """Ensure portal user is linked to the Customer via Portal User child table."""
    try:
        existing = frappe.db.exists("Portal User", {"user": user_email, "parent": customer, "parenttype": "Customer"})
        if not existing:
            customer_doc = frappe.get_doc("Customer", customer)
            customer_doc.append("portal_users", {"user": user_email})
            customer_doc.save(ignore_permissions=True)
            frappe.db.commit()
    except Exception:
        pass  # Non-fatal

def _check_doc_customer_permission(doctype, doc):
    if frappe.session.user == "Administrator":
        return True
        
    customer = get_current_customer()
    if not customer:
        # Not a portal customer - defer to standard role-based permissions
        return True
        
    docname = doc if isinstance(doc, str) else getattr(doc, "name", None)
    if docname:
        doc_customer = frappe.db.get_value(doctype, docname, "customer")
        if not doc_customer and docname.startswith("new-"):
            return True
    else:
        doc_customer = getattr(doc, "customer", None)
        if not doc_customer and getattr(doc, "is_new", lambda: False)():
            return True

    return doc_customer == customer

def has_sales_order_website_permission(doc, ptype, user, verbose=False):
    return _check_doc_customer_permission("Sales Order", doc)

def has_sales_invoice_website_permission(doc, ptype, user, verbose=False):
    return _check_doc_customer_permission("Sales Invoice", doc)

def has_customer_support_request_website_permission(doc, ptype, user, verbose=False):
    return _check_doc_customer_permission("Customer Support Request", doc)

def has_sales_order_permission(doc=None, ptype="read", user=None):
    """Desk & Web Form permission hook. Grant if it's the customer's own order, otherwise fallback to standard permissions."""
    # Allow permission for temporary/new docnames (e.g. web form initialization)
    if isinstance(doc, str) and doc.startswith("new-"):
        return True

    # Handle dict (new unsaved doc passed by run_doc_method)
    if isinstance(doc, dict):
        docname = doc.get("name", "") or ""
        if docname.startswith("new-") or not docname:
            return True

    customer = get_current_customer()
    if customer:
        if not doc:
            return True

        if isinstance(doc, str):
            doc_customer = frappe.db.get_value("Sales Order", doc, "customer")
        elif isinstance(doc, dict):
            doc_customer = doc.get("customer")
        else:
            doc_customer = getattr(doc, "customer", None)

        if doc_customer == customer:
            return True

        # New document without customer set yet
        docname = (doc if isinstance(doc, str) else (doc.get("name") if isinstance(doc, dict) else getattr(doc, "name", ""))) or ""
        if not doc_customer and (docname.startswith("new-") or not docname):
            return True

        # Customer portal user trying to access another customer's order - deny
        return False

    # Not a customer portal user (e.g., Salesman, internal user) -
    # return True to defer to standard role-based permission checks.
    # Returning None/False here would block the standard checks via
    # has_controller_permissions, causing spurious 403s for internal users
    # calling run_doc_method and other API endpoints.
    return True


@frappe.whitelist()
def get_logged_in_customer_details():
    customer = get_current_customer()
    customer_name = frappe.db.get_value("Customer", customer, "customer_name") if customer else ""
    return {
        "customer": customer,
        "customer_name": customer_name
    }

@frappe.whitelist()
def get_customer_credit_limit():
    from frappe.utils import flt
    customer = get_current_customer()
    if customer:
        limit = frappe.db.get_value("Customer Credit Limit", {"parent": customer}, "credit_limit")
        return flt(limit) if limit else 0.0
    return 0.0

@frappe.whitelist(allow_guest=False)
def get_item_search_results(doctype=None, txt="", searchfield=None, start=0, page_len=10, filters=None):
    from frappe.desk.reportview import get_match_cond

    txt = f"%{txt}%"
    return frappe.db.sql(f"""
        SELECT name as value, item_name as description 
        FROM `tabItem` 
        WHERE (name LIKE %s OR item_name LIKE %s)
        AND disabled = 0
        ORDER BY name ASC 
        LIMIT {int(start)}, {int(page_len)}
    """, (txt, txt), as_dict=True)

def get_portal_sidebar_items():
    return [
        {"title": "Dashboard", "route": "/portal", "label": "Dashboard"},
        {"title": "Place Order", "route": "/customer-order", "label": "Place Order"},
        {"title": "Pending Approvals", "route": "/customer-pending-approvals", "label": "Pending Approvals"},
        {"title": "My Ledger", "route": "/customer-ledger", "label": "My Ledger"},
        {"title": "Invoices", "route": "/customer-invoice", "label": "Invoices"},
        {"title": "Support Requests", "route": "/customer-support-request", "label": "Support Requests"},
    ]

def update_website_context(context):
    """
    Hook to automatically inject sidebar items and enable sidebar on portal pages and web forms.
    """
    path = getattr(context, "pathname", "") or frappe.request.path if hasattr(frappe, "request") and frappe.request else ""
    
    portal_routes = [
        "portal",
        "customer-order",
        "customer-invoice",
        "customer-ledger",
        "customer-support-request",
        "customer-pending-approvals",
    ]
    
    should_show_sidebar = False
    for r in portal_routes:
        if r in str(path):
            should_show_sidebar = True
            break
            
    if should_show_sidebar or getattr(context, "show_sidebar", 0):
        context.show_sidebar = 1
        context.sidebar_items = get_portal_sidebar_items()

@frappe.whitelist(allow_guest=False)
def get_item_rate(item_code):
    price = frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": "Standard Selling"}, "price_list_rate", ignore=1)
    if not price:
        price = frappe.db.get_value("Item Price", {"item_code": item_code}, "price_list_rate", ignore=1)
    if not price:
        price = frappe.db.get_value("Item", item_code, "standard_rate", ignore=1)
    return price or 0.0

@frappe.whitelist()
def approve_customer_order(order_name):
    customer = get_current_customer()
    if not customer:
        frappe.throw("Not permitted", frappe.PermissionError)
        
    doc = frappe.get_doc("Sales Order", order_name)
    if doc.customer != customer:
        frappe.throw("Not permitted", frappe.PermissionError)
        
    if doc.customer_approval_status != "Pending":
        frappe.throw("Order is not pending approval.")
        
    frappe.db.set_value("Sales Order", order_name, "customer_approval_status", "Approved")
    original_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        frappe.model.workflow.apply_workflow(doc, "Customer Approve")
    finally:
        frappe.set_user(original_user)
        
    return "Success"

@frappe.whitelist()
def reject_customer_order(order_name, reason):
    customer = get_current_customer()
    if not customer:
        frappe.throw("Not permitted", frappe.PermissionError)
        
    doc = frappe.get_doc("Sales Order", order_name)
    if doc.customer != customer:
        frappe.throw("Not permitted", frappe.PermissionError)
        
    if doc.customer_approval_status != "Pending":
        frappe.throw("Order is not pending approval.")
        
    original_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        frappe.model.workflow.apply_workflow(doc, "Customer Reject")
    finally:
        frappe.set_user(original_user)
    
    # We might want to store the reason in a custom field or comments, for now we add a comment
    doc.add_comment("Comment", text=f"Rejected by customer. Reason: {reason}")
    # add_comment saves the comment to the Communication table, no need to save the SO doc itself.
    return "Success"
def has_customer_ledger_website_permission(doc, ptype, user, verbose=False):
    return _check_doc_customer_permission("Customer Ledger", doc)

def sync_so_packed_status(doc, method):
    # Update linked Sales Orders to 'Packed' if they are 'Customer Approved'
    sales_orders = set([loc.sales_order for loc in doc.locations if loc.sales_order])
    for so_name in sales_orders:
        current_state = frappe.db.get_value("Sales Order", so_name, "workflow_state")
        if current_state in ["Customer Approved", "Approved"]:
            frappe.db.set_value("Sales Order", so_name, "workflow_state", "Packed")

def sync_so_dispatched_status(doc, method):
    # Update linked Sales Orders to 'Dispatched'
    sales_orders = set([item.against_sales_order for item in doc.items if item.against_sales_order])
    for so_name in sales_orders:
        current_state = frappe.db.get_value("Sales Order", so_name, "workflow_state")
        # Only update if it's currently Packed or Customer Approved
        if current_state in ["Packed", "Customer Approved", "Approved", "Ready for Dispatch"]:
            frappe.db.set_value("Sales Order", so_name, "workflow_state", "Dispatched")

@frappe.whitelist()
def has_unsubmitted_delivery_documents(sales_order_name):
    # Check if there are any Draft (docstatus=0) Delivery Notes or Pick Lists
    has_dn = frappe.db.exists("Delivery Note Item", {
        "against_sales_order": sales_order_name,
        "docstatus": 0
    })
    has_pl = frappe.db.exists("Pick List Item", {
        "sales_order": sales_order_name,
        "docstatus": 0
    })
    return bool(has_dn or has_pl)

@frappe.whitelist()
def check_advance_payment_needed_for_invoice(invoice_name):
    # Check if any linked Sales Order requires advance payment
    if not invoice_name:
        return False
    doc = frappe.get_doc("Sales Invoice", invoice_name)
    if not doc.items:
        return False
    for item in doc.items:
        if item.sales_order:
            req = frappe.db.get_value("Sales Order", item.sales_order, "requires_advance_payment")
            if req:
                adv = frappe.db.get_value("Sales Order", item.sales_order, "advance_paid") or 0
                tot = frappe.db.get_value("Sales Order", item.sales_order, "grand_total") or 0
                if frappe.utils.flt(adv) < frappe.utils.flt(tot):
                    return item.sales_order
    return False
