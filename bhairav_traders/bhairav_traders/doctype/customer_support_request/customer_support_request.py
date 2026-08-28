import frappe
from frappe.model.document import Document
from frappe.utils import today

class CustomerSupportRequest(Document):
    def validate(self):
        if not self.posting_date:
            self.posting_date = today()
        if not self.status:
            self.status = "Open"
            
        if not self.customer:
            from bhairav_traders.portal_utils import get_current_customer
            customer = get_current_customer()
            if customer:
                self.customer = customer
                
        if self.customer and not self.email:
            self.email = frappe.db.get_value("Customer", self.customer, "email_id")
