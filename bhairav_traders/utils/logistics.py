import frappe
from frappe import _

def delivery_note_before_save(doc, method=None):
    """
    Handle QC automation for Delivery Notes.
    """
    if doc.workflow_state == "Approved & Dispatched":
        # If the QC has just been approved, record who did it.
        if not doc.qc_checked_by:
            doc.qc_checked_by = frappe.session.user
    elif doc.workflow_state == "Pending QC Verification":
        # Reset if sent back
        doc.qc_checked_by = None

    requires_validation = (doc.workflow_state and doc.workflow_state != "Draft") or doc.docstatus == 1
    if requires_validation:
        if not doc.shipping_address_name:
            frappe.throw(_("Dispatch Blocked: Shipping Address is required."))
            
        # Assume Transporter Details mean transporter or distance
        if not getattr(doc, "transporter", None) and not getattr(doc, "distance", None):
            frappe.throw(_("E-Way Bill Blocked: Transporter Details are missing. Please provide Transporter or Distance."))

def validate_single_pick_list(doc, method=None):
    """
    Ensure only 1 active Pick List is created per Sales Order.
    """
    sales_orders = []
    for item in doc.locations:
        if item.sales_order and item.sales_order not in sales_orders:
            sales_orders.append(item.sales_order)
            
    if not sales_orders:
        return
        
    for so in sales_orders:
        existing = frappe.db.sql("""
            SELECT parent FROM `tabPick List Item`
            WHERE sales_order = %s AND parent != %s
            AND parent IN (SELECT name FROM `tabPick List` WHERE docstatus < 2)
        """, (so, doc.name))
        
        if existing:
            frappe.throw(_("A Pick List ({0}) already exists for Sales Order {1}. Only one Pick List is allowed per Sales Order!").format(existing[0][0], so))
