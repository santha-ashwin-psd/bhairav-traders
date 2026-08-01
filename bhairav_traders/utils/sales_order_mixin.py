import frappe
from bhairav_traders.portal_utils import get_current_customer


class SalesOrderPortalMixin:
	def _submit(self):
		if frappe.session.user != "Administrator":
			customer = get_current_customer()
			if customer:
				doc_customer = getattr(self, "customer", None)
				if doc_customer == customer:
					self.flags.ignore_permissions = True
		return super()._submit()
