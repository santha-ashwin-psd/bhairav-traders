app_name = "bhairav_traders"
app_title = "Bhairav Traders"
app_publisher = "Bhairav Traders"
app_description = "Customizations for Bhairav Traders"
app_email = "admin@bhairavtraders.com "
app_license = "mit"
app_logo_url = "/assets/bhairav_traders/logo.png"
brand_html = '<div class="d-flex align-items-center"><img src="/assets/bhairav_traders/logo.png" style="height: 40px; margin-right: 10px;"><span style="font-weight: bold; font-size: 1.25rem; vertical-align: middle;">Bhairav Traders</span></div>'

# Apps
# ------------------

# required_apps = []	

add_to_apps_screen = [
	{
		"name": "bhairav_traders",
		"logo": "/assets/bhairav_traders/logo.png",
		"title": "Bhairav Traders",
		"route": "/portal"
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/bhairav_traders/css/bhairav_traders.css"
# app_include_js = "/assets/bhairav_traders/js/bhairav_traders.js"

# include js, css files in header of web template
web_include_css = "/assets/bhairav_traders/css/customer_portal.css?v=24"
web_include_js = "/assets/bhairav_traders/js/customer_portal.js?v=1"

standard_portal_menu_items = [
	{"title": "Dashboard", "route": "/portal", "role": "Customer"},
	{"title": "Place Order", "route": "/customer-order", "role": "Customer"},
	{"title": "Pending Approvals", "route": "/customer-pending-approvals", "role": "Customer"},
	{"title": "My Ledger", "route": "/customer-ledger", "role": "Customer"},
	{"title": "Invoices", "route": "/customer-invoice", "role": "Customer"},
	{"title": "Support Requests", "route": "/customer-support-request", "role": "Customer"},
]

update_website_context = "bhairav_traders.portal_utils.update_website_context"

has_website_permission = {
	"Sales Order": "bhairav_traders.portal_utils.has_sales_order_website_permission",
	"Sales Invoice": "bhairav_traders.portal_utils.has_sales_invoice_website_permission",
	"Customer Support Request": "bhairav_traders.portal_utils.has_customer_support_request_website_permission",
	"Customer Ledger": "bhairav_traders.portal_utils.has_customer_ledger_website_permission",
}
# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "bhairav_traders/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "bhairav_traders/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "bhairav_traders.utils.jinja_methods",
# 	"filters": "bhairav_traders.utils.jinja_filters"
# }

# Installation
# ------------


# before_install = "bhairav_traders.install.before_install"
after_install = "bhairav_traders.install.after_install"
after_migrate = "bhairav_traders.custom_fields.setup_custom_fields"

# Uninstallation
# ------------

# before_uninstall = "bhairav_traders.uninstall.before_uninstall"
# after_uninstall = "bhairav_traders.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "bhairav_traders.utils.before_app_install"
# after_app_install = "bhairav_traders.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "bhairav_traders.utils.before_app_uninstall"
# after_app_uninstall = "bhairav_traders.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "bhairav_traders.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "bhairav_traders.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
has_permission = {
	"Sales Order": "bhairav_traders.portal_utils.has_sales_order_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Order": {
		"validate": "bhairav_traders.credit_limit.validate_sales_order_credit",
		"after_insert": "bhairav_traders.credit_limit.after_insert_sales_order"
	},
	"Sales Invoice": {
		"before_submit": [
			"bhairav_traders.credit_limit.validate_sales_invoice_locking",
			"bhairav_traders.credit_limit.validate_advance_payment"
		],
		"on_submit": "bhairav_traders.credit_limit.sales_invoice_on_submit"
	},
	"Delivery Note": {
		"before_submit": "bhairav_traders.credit_limit.validate_advance_payment"
	},
	"Payment Entry": {
		"on_submit": "bhairav_traders.discount.payment_entry_on_submit"
	},
	"Sales Person": {
		"before_validate": "bhairav_traders.utils.sales_person.before_validate_sales_person",
		"validate": "bhairav_traders.utils.sales_person.validate_sales_person"
	},
	"GL Entry": {
		"before_insert": "bhairav_traders.utils.gl_entry_sync.gl_entry_before_insert",
		"after_insert": "bhairav_traders.utils.gl_entry_sync.on_gl_entry_insert",
		"on_trash": "bhairav_traders.utils.gl_entry_sync.on_gl_entry_trash"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"bhairav_traders.credit_limit.sync_all_customer_lock_statuses"
	]
}

# Testing
# -------

# before_tests = "bhairav_traders.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
extend_doctype_class = {
	"Sales Order": "bhairav_traders.utils.sales_order_mixin.SalesOrderPortalMixin"
}

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "bhairav_traders.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "bhairav_traders.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["bhairav_traders.portal_utils.before_request"]
# after_request = ["bhairav_traders.utils.after_request"]

# Job Events
# ----------
# before_job = ["bhairav_traders.utils.before_job"]
# after_job = ["bhairav_traders.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"bhairav_traders.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []