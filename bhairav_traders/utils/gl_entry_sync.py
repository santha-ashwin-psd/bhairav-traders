import frappe

def get_current_balance(customer):
	# Calculate current balance from existing Customer Ledger records
	result = frappe.db.sql("""
		SELECT SUM(debit) - SUM(credit)
		FROM `tabCustomer Ledger`
		WHERE customer = %s
	""", (customer,))
	
	return result[0][0] if result and result[0][0] else 0.0

def gl_entry_before_insert(doc, method):
	from frappe.model.naming import set_name_from_naming_options
	set_name_from_naming_options(doc.meta.autoname, doc)
	doc.to_rename = 0

def on_gl_entry_insert(doc, method):
	if doc.party_type == "Customer" and doc.party:
		# Get previous balance
		current_balance = get_current_balance(doc.party)
		
		# Calculate new balance
		new_balance = current_balance + (doc.debit or 0.0) - (doc.credit or 0.0)
		
		# Create Customer Ledger entry
		ledger_entry = frappe.get_doc({
			"doctype": "Customer Ledger",
			"customer": doc.party,
			"posting_date": doc.posting_date,
			"voucher_type": doc.voucher_type,
			"voucher_no": doc.voucher_no,
			"against": doc.against,
			"debit": doc.debit,
			"credit": doc.credit,
			"balance": new_balance,
			"remarks": doc.remarks,
			"gl_entry": doc.name
		})
		ledger_entry.insert(ignore_permissions=True)

def on_gl_entry_trash(doc, method):
	if doc.party_type == "Customer" and doc.party:
		# Find linked Customer Ledger entry
		ledger_entries = frappe.get_all(
			"Customer Ledger", 
			filters={"gl_entry": doc.name},
			pluck="name"
		)
		
		for entry_name in ledger_entries:
			frappe.delete_doc("Customer Ledger", entry_name, ignore_permissions=True)
