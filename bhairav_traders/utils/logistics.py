import frappe

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
