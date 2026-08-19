import frappe
from frappe.utils import get_first_day, get_last_day, add_months, today

def apply_dealer_scheme_discount(doc, method=None):
    """
    Check if the customer met their monthly target last month.
    If yes, automatically apply the scheme discount to this Sales Order.
    """
    if not doc.customer:
        return
        
    customer = frappe.get_doc("Customer", doc.customer)
    
    if not customer.get("dealer_monthly_target") or not customer.get("scheme_discount_percentage"):
        return
        
    # We only auto-apply if they haven't manually set a discount
    if doc.additional_discount_percentage > 0:
        return
        
    # Calculate previous month's date range
    prev_month_date = add_months(today(), -1)
    start_date = get_first_day(prev_month_date)
    end_date = get_last_day(prev_month_date)
    
    # Get total sales for previous month
    total_sales = frappe.db.sql("""
        SELECT SUM(grand_total) 
        FROM `tabSales Invoice` 
        WHERE customer = %s 
        AND docstatus = 1 
        AND posting_date >= %s 
        AND posting_date <= %s
    """, (customer.name, start_date, end_date))[0][0]
    
    if not total_sales:
        total_sales = 0
        
    if total_sales >= customer.dealer_monthly_target:
        # Target Achieved! Apply discount
        doc.additional_discount_percentage = customer.scheme_discount_percentage
        frappe.msgprint(f"🎉 <b>Dealer Scheme Activated!</b> {customer.name} met their target of ₹{customer.dealer_monthly_target} last month. An automatic {customer.scheme_discount_percentage}% discount has been applied.", alert=True, indicator="green")
