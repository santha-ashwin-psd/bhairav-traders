import frappe

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
        return False
    docname = doc if isinstance(doc, str) else getattr(doc, "name", None)
    if docname:
        doc_customer = frappe.db.get_value(doctype, docname, "customer")
    else:
        doc_customer = getattr(doc, "customer", None)

    return doc_customer == customer

def has_sales_order_website_permission(doc, ptype, user, verbose=False):
    return _check_doc_customer_permission("Sales Order", doc)

def has_sales_invoice_website_permission(doc, ptype, user, verbose=False):
    return _check_doc_customer_permission("Sales Invoice", doc)

def has_customer_support_request_website_permission(doc, ptype, user, verbose=False):
    return _check_doc_customer_permission("Customer Support Request", doc)

def has_sales_order_permission(doc, ptype="read", user=None):
    """Desk & Web Form permission hook. Grant if it's the customer's own order, otherwise fallback to standard permissions."""
    customer = get_current_customer()
    if customer:
        docname = doc if isinstance(doc, str) else getattr(doc, "name", None)
        if docname:
            doc_customer = frappe.db.get_value("Sales Order", docname, "customer")
        else:
            doc_customer = getattr(doc, "customer", None)
            
        if doc_customer == customer:
            return True
            
    return None


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
        
    frappe.db.set_value("Sales Order", order_name, "customer_approval_status", "Rejected")
    
    # We might want to store the reason in a custom field or comments, for now we add a comment
    doc.add_comment("Comment", text=f"Rejected by customer. Reason: {reason}")
    # add_comment saves the comment to the Communication table, no need to save the SO doc itself.
    return "Success"