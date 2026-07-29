import json
import frappe
from frappe import _
from frappe.utils import flt, today, add_days
from bhairav_traders.credit_limit import check_account_lock_status

login_required = 1
no_cache = 1

def get_current_customer():
    if frappe.session.user == "Guest":
        return None
    portal_user = frappe.db.get_value("Portal User", {"user": frappe.session.user}, "parent")
    if portal_user:
        return portal_user
    contact = frappe.db.get_value("Contact", {"email_id": frappe.session.user})
    if contact:
        customer = frappe.db.get_value("Dynamic Link", {"parent": contact, "link_doctype": "Customer"}, "link_name")
        if customer:
            return customer
    return frappe.db.get_value("Customer", {"email_id": frappe.session.user})

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/portal/place_order"
        raise frappe.Redirect

    customer = get_current_customer()
    context.customer = customer
    context.customer_name = frappe.db.get_value("Customer", customer, "customer_name") if customer else "Customer"

    # Check account lock status
    if customer:
        context.is_locked = check_account_lock_status(customer)
        context.lock_reason = frappe.db.get_value("Customer", customer, "lock_reason")
    else:
        context.is_locked = False
        context.lock_reason = ""

    context.show_sidebar = 1

    # Get items available for ordering
    items = frappe.db.sql("""
        SELECT
            name as item_code,
            item_name,
            item_group,
            stock_uom,
            image,
            description,
            standard_rate
        FROM `tabItem`
        WHERE disabled = 0 AND is_sales_item = 1
        ORDER BY item_name ASC
        LIMIT 100
    """, as_dict=True)

    for item in items:
        price = frappe.db.get_value("Item Price", {
            "item_code": item.item_code,
            "buying": 0,
            "selling": 1
        }, "price_list_rate")
        item.rate = flt(price) if price else flt(item.standard_rate)

    context.items = items

@frappe.whitelist()
def create_customer_order(items_json):
    if frappe.session.user == "Guest":
        frappe.throw(_("Please login to place an order"))

    customer = get_current_customer()
    if not customer:
        frappe.throw(_("No customer account linked to your profile."))

    if check_account_lock_status(customer):
        lock_reason = frappe.db.get_value("Customer", customer, "lock_reason")
        frappe.throw(_("Your account is locked due to overdue payments. Reason: {0}").format(lock_reason))

    if isinstance(items_json, str):
        items_list = json.loads(items_json)
    else:
        items_list = items_json

    if not items_list:
        frappe.throw(_("Cart is empty. Please select at least one item."))

    company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")

    so = frappe.new_doc("Sales Order")
    so.customer = customer
    so.company = company
    so.delivery_date = add_days(today(), 7)
    so.order_type = "Sales"
    so.placed_by_salesman = 0
    so.customer_approval_status = "Not Required"

    for item in items_list:
        item_code = item.get("item_code")
        qty = flt(item.get("qty"))
        rate = flt(item.get("rate"))

        if qty <= 0:
            continue

        so.append("items", {
            "item_code": item_code,
            "qty": qty,
            "rate": rate,
            "delivery_date": add_days(today(), 7)
        })

    if not so.items:
        frappe.throw(_("Invalid order items or zero quantities."))

    frappe.flags.ignore_permissions = True
    try:
        so.insert(ignore_permissions=True)
    finally:
        frappe.flags.ignore_permissions = False

    return {
        "status": "success",
        "name": so.name,
        "requires_advance": getattr(so, "requires_advance_payment", 0),
        "message": _("Order {0} successfully created!").format(so.name)
    }
