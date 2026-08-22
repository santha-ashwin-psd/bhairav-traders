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

def send_due_today_alerts():
    """
    Find unpaid Sales Invoices due today and alert the Accounts Executive team.
    """
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "outstanding_amount": (">", 0),
            "due_date": today()
        },
        fields=["name", "customer_name", "outstanding_amount", "due_date"]
    )
    if not invoices:
        return
        
    accounts_executives = frappe.db.sql("""
        SELECT parent FROM `tabHas Role`
        WHERE role='Accounts Executive' AND parenttype='User'
    """, as_dict=True)
    emails = [frappe.db.get_value("User", u.parent, "email") for u in accounts_executives]
    emails = [e for e in emails if e]
    
    if emails:
        for inv in invoices:
            subject = f"Alert: Invoice {inv.name} is due today"
            message = f"Hello Accounts Team,<br><br>Invoice {inv.name} for {inv.customer_name} (Amount: ₹{inv.outstanding_amount:,.2f}) is due today ({inv.due_date}).<br>Please follow up."
            frappe.sendmail(recipients=emails, subject=subject, message=message)

def send_overdue_warnings():
    """
    Find unpaid Sales Invoices 1-7 days overdue and alert the Salesperson.
    """
    one_day_ago = add_days(today(), -1)
    seven_days_ago = add_days(today(), -7)
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "outstanding_amount": (">", 0),
            "due_date": ["between", [seven_days_ago, one_day_ago]]
        },
        fields=["name", "customer_name", "outstanding_amount", "due_date", "owner"]
    )
    
    for inv in invoices:
        sales_user_email = frappe.db.get_value("User", inv.owner, "email")
        if sales_user_email:
            subject = f"Warning: Invoice {inv.name} is overdue (1-7 days)"
            message = f"Hello,<br><br>Invoice {inv.name} for {inv.customer_name} is overdue. The due date was {inv.due_date} (Amount: ₹{inv.outstanding_amount:,.2f}).<br>Please follow up with the customer."
            frappe.sendmail(recipients=[sales_user_email], subject=subject, message=message)
