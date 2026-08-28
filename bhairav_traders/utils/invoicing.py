import frappe

def validate_eway_bill(doc, method=None):
    """
    Ensure E-Way Bill No is provided for Sales Invoices over ₹50,000.
    """
    if doc.grand_total > 50000:
        if not doc.get("e_way_bill_no"):
            try:
                template = frappe.get_doc("Email Template", "ATU-EMAIL-728")
                message = frappe.render_template(template.response_html, {"doc": doc})
                frappe.sendmail(
                    recipients=[frappe.session.user],
                    subject=frappe.render_template(template.subject, {"doc": doc}),
                    message=message,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name
                )
            except Exception:
                pass
            frappe.throw("An E-Way Bill No is mandatory for invoices exceeding ₹50,000 as per GST compliance rules.")
