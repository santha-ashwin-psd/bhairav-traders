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
        from erpnext.controllers.sales_and_purchase_return import make_return_doc
        
        # Create a proper return document linked to the original invoice
        cn = make_return_doc("Sales Invoice", invoice.name)
        cn.posting_date = invoice.posting_date
        cn.update_outstanding_for_self = 0
        cn.remarks = f"Early Payment Discount of {discount_pct}% for invoice {invoice.name} paid within {days_taken} days (Payment Entry: {payment_entry_name})"
        
        # Keep only the first item (to maintain the internal link) and delete the rest
        first_item = cn.items[0]
        cn.set("items", [first_item])
        
        # Modify this existing item to be our discount line
        first_item.qty = -1.0
        first_item.rate = discount_amount
        first_item.amount = -discount_amount
        first_item.description = f"Early Payment Discount ({discount_pct}%)"
        
        cn.flags.ignore_permissions = True
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

def sales_invoice_validate_pricing(doc, method=None):
    """
    Auto-populates the custom_pricing_rule and custom_promotional_scheme
    fields on Sales Invoice items based on the hidden pricing_rules field.
    """
    if not getattr(doc, "items", None):
        return
        
    for item in doc.items:
        if getattr(item, "pricing_rules", None):
            pr_value = item.pricing_rules
            pr_name = None
            try:
                parsed = frappe.parse_json(pr_value)
                if isinstance(parsed, list) and parsed:
                    pr_name = parsed[0]
                elif isinstance(parsed, str):
                    pr_name = parsed
            except Exception:
                pr_name = str(pr_value).split(",")[0].strip()
                
            if not pr_name:
                continue

            item.custom_pricing_rule = pr_name
            
            # Retrieve the promotional scheme from the Pricing Rule
            if frappe.db.exists("Pricing Rule", pr_name):
                promo_scheme = frappe.db.get_value("Pricing Rule", pr_name, "promotional_scheme")
                if promo_scheme:
                    item.custom_promotional_scheme = promo_scheme
