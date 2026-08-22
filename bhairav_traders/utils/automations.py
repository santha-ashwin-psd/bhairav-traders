import frappe
from frappe.utils import add_days, today

def send_payment_reminders():
    """
    Find unpaid Sales Invoices due in exactly 7 days and send an email reminder to the customer.
    """
    due_date = add_days(today(), 7)
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "outstanding_amount": (">", 0),
            "due_date": due_date
        },
        fields=["name", "customer", "customer_name", "outstanding_amount", "due_date"]
    )
    
    for inv in invoices:
        customer_email = frappe.db.get_value("Contact", {"link_doctype": "Customer", "link_name": inv.customer, "is_primary_contact": 1}, "email_id")
        if not customer_email:
            customer_email = frappe.db.get_value("Customer", inv.customer, "email_id")
            
        if customer_email:
            subject = f"Payment Reminder: Invoice {inv.name} due in 7 days"
            message = f"Dear {inv.customer_name},<br><br>This is a gentle reminder that your payment of ₹{inv.outstanding_amount:,.2f} for Invoice {inv.name} is due on {inv.due_date}.<br><br>Thank you."
            frappe.sendmail(
                recipients=[customer_email],
                subject=subject,
                message=message
            )

def send_pending_order_alerts():
    """
    Find Sales Orders in Draft or Pending Approval for more than 3 days and alert the Salesperson.
    """
    three_days_ago = add_days(today(), -3)
    orders = frappe.get_all(
        "Sales Order",
        filters={
            "docstatus": 0,
            "workflow_state": ("in", ["Draft", "Pending Sales Manager Approval", "Pending Regional Manager Approval", "Pending Sales Head Approval", "Pending Director Approval", "Pending Commercial Credit Check", "Pending Customer Approval"]),
            "creation": ("<", three_days_ago)
        },
        fields=["name", "owner", "workflow_state", "creation"]
    )
    
    for order in orders:
        sales_user_email = frappe.db.get_value("User", order.owner, "email")
        if sales_user_email:
            subject = f"Alert: Sales Order {order.name} pending for too long"
            message = f"Hello,<br><br>Sales Order {order.name} has been stuck in state '{order.workflow_state}' since {order.creation}. Please take action.<br><br>Thank you."
            frappe.sendmail(
                recipients=[sales_user_email],
                subject=subject,
                message=message
            )
