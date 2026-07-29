import frappe
from bhairav_traders.portal_utils import update_website_context, get_current_customer


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/customer-pending-approvals"
		raise frappe.Redirect

	update_website_context(context)

	customer = get_current_customer()
	if not customer:
		frappe.throw("No customer account linked to this user.", frappe.PermissionError)

	context.customer = customer


def get_list_context(context):
	update_website_context(context)
	context.get_list = get_pending_approvals


def get_pending_approvals(
	doctype, txt=None, filters=None,
	limit_start=0, limit_page_length=20,
	order_by="creation desc", **kwargs
):
	customer = get_current_customer()
	if not customer:
		return []

	return frappe.get_all(
		"Sales Order",
		filters={
			"customer": customer,
			"customer_approval_status": "Pending",
		},
		fields=["name", "transaction_date", "grand_total", "customer_approval_status"],
		order_by="creation desc",
		limit_start=limit_start,
		limit_page_length=limit_page_length,
		ignore_permissions=True,
	)


def has_website_permission(doc, ptype, user, verbose=False):
	"""Allow customer to open only their own Sales Orders on portal."""
	customer = get_current_customer()
	if customer and doc.customer == customer:
		return True
	return False