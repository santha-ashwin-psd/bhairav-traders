import frappe
from frappe import _
import frappe.model.workflow

login_required = 1


def get_current_customer():
	if frappe.session.user == "Guest":
		return None

	# Try Portal User table first
	portal_user = frappe.db.get_value(
		"Portal User", {"user": frappe.session.user}, "parent"
	)
	if portal_user:
		return portal_user

	# Try Contact → Dynamic Link → Customer
	contact = frappe.db.get_value(
		"Contact", {"email_id": frappe.session.user}, "name"
	)
	if contact:
		customer = frappe.db.get_value(
			"Dynamic Link",
			{"parent": contact, "link_doctype": "Customer"},
			"link_name",
		)
		if customer:
			return customer

	# Try Customer email_id directly
	return frappe.db.get_value(
		"Customer", {"email_id": frappe.session.user}, "name"
	)


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/customer-pending-approvals"
		raise frappe.Redirect

	customer = get_current_customer()
	if not customer:
		context.orders = []
		context.error = "No customer account linked to this user."
		return

	context.customer = customer
	context.orders = frappe.get_all(
		"Sales Order",
		filters={
			"customer": customer,
			"customer_approval_status": "Pending",
			"docstatus": 0,
		},
		fields=[
			"name", "transaction_date", "grand_total",
			"po_no", "status", "currency", "owner",
		],
		ignore_permissions=True,
	)


@frappe.whitelist()
def approve_order(order_id):
	# Auth check
	if frappe.session.user == "Guest":
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	customer = get_current_customer()
	if not customer:
		frappe.throw(_("No customer account linked to this user."), frappe.PermissionError)

	# Fetch the Sales Order
	doc = frappe.get_doc("Sales Order", order_id)

	# Verify this order belongs to this customer
	if doc.customer != customer:
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	# Verify it is still pending
	if doc.customer_approval_status != "Pending":
		frappe.throw(_("This order is no longer pending approval."))

	# Update status and workflow state
	frappe.db.set_value("Sales Order", doc.name, "customer_approval_status", "Approved")
	original_user = frappe.session.user
	frappe.set_user("Administrator")
	try:
		frappe.model.workflow.apply_workflow(doc, "Customer Approve")
	finally:
		frappe.set_user(original_user)
	
	return {"status": "success", "message": f"Order {order_id} approved!"}


@frappe.whitelist()
def reject_order(order_id, reason=""):
	# Auth check
	if frappe.session.user == "Guest":
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	customer = get_current_customer()
	if not customer:
		frappe.throw(_("No customer account linked to this user."), frappe.PermissionError)

	# Fetch the Sales Order
	doc = frappe.get_doc("Sales Order", order_id)

	# Verify this order belongs to this customer
	if doc.customer != customer:
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	# Verify it is still pending
	if doc.customer_approval_status != "Pending":
		frappe.throw(_("This order is no longer pending approval."))

	# Update status and workflow state
	original_user = frappe.session.user
	frappe.set_user("Administrator")
	try:
		frappe.model.workflow.apply_workflow(doc, "Customer Reject")
	finally:
		frappe.set_user(original_user)

	return {"status": "success", "message": f"Order {order_id} rejected!"}