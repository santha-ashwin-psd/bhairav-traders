import frappe
from frappe.model.document import Document
from frappe.utils import today

class CustomerLedger(Document):
    def validate(self):
        if not self.posting_date:
            self.posting_date = today()
