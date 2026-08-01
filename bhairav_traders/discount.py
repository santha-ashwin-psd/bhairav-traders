import frappe
from frappe import _
from frappe.utils import flt, date_diff, getdate

def payment_entry_on_submit(doc, method=None):
    """
    Triggered on Payment Entry submit.
    Checks linked Sales Invoices for early payment discount:
    - Paid within 15 days of invoice date: 3% discount as Credit Note
    - Paid within 30 days of invoice date: 2% discount as Credit Note
    - Paid within 45 days of invoice date: 1% discount as Credit Note
    """
    if doc.payment_type != "Receive" or not doc.references:
        return
        
    payment_date = getdate(doc.posting_date)
    
    for ref in doc.references:
        if ref.reference_doctype != "Sales Invoice" or not ref.reference_name:
            continue
            
        invoice = frappe.get_doc("Sales Invoice", ref.reference_name)
        invoice_date = getdate(invoice.posting_date)
        days = date_diff(payment_date, invoice_date)
        
        if days < 0:
            continue
            
        discount_pct = 0.0
        if days <= 15:
            discount_pct = 3.0
        elif days <= 30:
            discount_pct = 2.0
        elif days <= 45:
            discount_pct = 1.0
            
        if discount_pct > 0:
            allocated_amount = flt(ref.allocated_amount)
            discount_amount = flt(allocated_amount * (discount_pct / 100.0), 2)
            
            if discount_amount > 0:
                create_early_payment_credit_note(
                    invoice=invoice,
                    payment_entry_name=doc.name,
                    discount_pct=discount_pct,
                    discount_amount=discount_amount,
                    days_taken=days
                )


def create_early_payment_credit_note(invoice, payment_entry_name, discount_pct, discount_amount, days_taken):
    """
    Creates and submits a Credit Note (Sales Invoice return or Standalone Credit Note) for early payment discount.
    """
    try:
        cn = frappe.new_doc("Sales Invoice")
        cn.is_return = 1
        cn.customer = invoice.customer
        cn.company = invoice.company
        cn.posting_date = invoice.posting_date
        cn.currency = invoice.currency
        cn.remarks = f"Early Payment Discount of {discount_pct}% for invoice {invoice.name} paid within {days_taken} days (Payment Entry: {payment_entry_name})"
        
        # Add item for discount
        item_code = invoice.items[0].item_code if invoice.items else None
        
        cn.append("items", {
            "item_code": item_code,
            "qty": -1,
            "rate": discount_amount,
            "amount": -discount_amount,
            "description": f"Early Payment Discount ({discount_pct}%)"
        })
        
        frappe.flags.ignore_permissions = True
        cn.insert(ignore_permissions=True)
        cn.submit()
        
        frappe.msgprint(
            _("Early Payment Discount Credit Note {0} of ₹{1:,.2f} ({2}%) generated successfully for Invoice {3}.").format(
                cn.name, discount_amount, discount_pct, invoice.name
            )
        )
    except Exception as e:
        frappe.log_error(f"Error auto-generating Credit Note for Payment Entry {payment_entry_name}: {e}")
        frappe.msgprint(_("Could not auto-generate Credit Note for early payment discount: {0}").format(str(e)))
