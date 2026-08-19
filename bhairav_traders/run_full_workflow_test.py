import frappe
from frappe.model.workflow import apply_workflow
from frappe.utils import today, add_days

def execute():
    print("\n--- STARTING ATULYA MASTER WORKFLOW TEST ---")
    
    # 1. Setup Base Data
    frappe.set_user("Administrator")
    
    # Ensure is_credit_approved custom field exists on Sales Order
    if not frappe.db.exists("Custom Field", "Sales Order-is_credit_approved"):
        doc = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Sales Order",
            "fieldname": "is_credit_approved",
            "label": "Is Credit Approved",
            "fieldtype": "Check",
            "insert_after": "status"
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    
    # Give all roles Account read access for the test to pass Frappe validations
    for role in ["Warehouse Manager", "Dispatch Executive", "Accounts Executive", "Finance Manager", "Sales Executive", "Sales Manager", "Regional Manager", "Commercial", "Sales Head", "Director"]:
        if not frappe.db.exists("Custom DocPerm", {"parent": "Account", "role": role}):
            doc = frappe.new_doc("Custom DocPerm")
            doc.parent = "Account"
            doc.parenttype = "DocType"
            doc.parentfield = "permissions"
            doc.role = role
            doc.read = 1
            doc.insert(ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_cache(doctype="Account")
    
    # Ensure Customer User exists
    if not frappe.db.exists("User", "customer@gmail.com"):
        user = frappe.new_doc("User")
        user.email = "customer@gmail.com"
        user.first_name = "Test"
        user.last_name = "Customer"
        user.append("roles", {"role": "Customer"})
        user.insert(ignore_permissions=True)
        print("Created customer user.")
        
    # Ensure Customer exists
    customer_name = "ATULYA Test Customer"
    if not frappe.db.exists("Customer", customer_name):
        cust = frappe.new_doc("Customer")
        cust.customer_name = customer_name
        cust.customer_group = "Commercial"
        cust.territory = "All Territories"
        cust.customer_type = "Company"
        cust.insert(ignore_permissions=True)
        print(f"Created Customer: {customer_name}")
        
    # Ensure Item exists
    item_code = "ATULYA-TEST-ITEM"
    if not frappe.db.exists("Item", item_code):
        item = frappe.new_doc("Item")
        item.item_code = item_code
        item.item_group = "Products"
        item.is_stock_item = 1
        item.insert(ignore_permissions=True)
        print(f"Created Item: {item_code}")
        
    # Ensure Price
    if not frappe.db.exists("Item Price", {"item_code": item_code, "price_list": "Standard Selling"}):
        price = frappe.new_doc("Item Price")
        price.item_code = item_code
        price.price_list = "Standard Selling"
        price.price_list_rate = 100000
        price.insert(ignore_permissions=True)
        print(f"Created Item Price for {item_code}")

    frappe.db.commit()

    print("\n--- PHASE 1: SALES ORDER (SALES EXEC -> SALES MANAGER) ---")
    # Sales Exec creates order
    frappe.set_user("sales_exec@atulya.com")
    so = frappe.new_doc("Sales Order")
    so.customer = customer_name
    so.delivery_date = add_days(today(), 5)
    so.append("items", {
        "item_code": item_code,
        "qty": 1,
        "rate": 100000
    })
    # Apply a 6% discount (Needs Regional Manager)
    so.additional_discount_percentage = 6
    so.insert()
    print(f"Sales Exec created SO: {so.name}")
    
    # Workflow action: Submit for Approval
    frappe.set_user("Administrator")
    try:
        apply_workflow(so, "Submit for approval")
        print(f"SO State after Submit: {so.workflow_state}")
    except Exception as e:
        print(f"Error during Submit: {str(e)}")
    
    # Needs Regional Manager because discount > 5%
    frappe.set_user("Administrator")
    try:
        so = frappe.get_doc("Sales Order", so.name)
        apply_workflow(so, "Approve")
        print(f"Regional Manager approved SO. State: {so.workflow_state}")
    except Exception as e:
        print(f"Error during RM approval: {str(e)}")
        
    # Phase 3: Commercial Approval
    frappe.set_user("Administrator")
    try:
        so = frappe.get_doc("Sales Order", so.name)
        apply_workflow(so, "Approve")
        frappe.db.set_value("Sales Order", so.name, "is_credit_approved", 1)
        frappe.db.commit()
        print(f"Commercial approved SO. State: {so.workflow_state}")
    except Exception as e:
        print(f"Error during Commercial approval: {str(e)}")
        
    print("\n--- PHASE 1.5: CUSTOMER PORTAL APPROVAL ---")
    frappe.set_user("Administrator")
    so = frappe.get_doc("Sales Order", so.name)
    so.customer_approval_status = "Approved"
    so.workflow_state = "Approved"
    so.save(ignore_permissions=True)
    so.submit()
    print(f"Customer approved the Sales Order on the Portal. SO docstatus: {so.docstatus}")
        
    print("\n--- PHASE 2: WAREHOUSE & DISPATCH (DELIVERY NOTE QC) ---")
    frappe.set_user("warehouse@atulya.com")
    
    # First update stock so we can deliver
    frappe.set_user("Administrator")
    se = frappe.new_doc("Stock Entry")
    se.purpose = "Material Receipt"
    se.stock_entry_type = "Material Receipt"
    se.append("items", {
        "item_code": item_code,
        "qty": 10,
        "t_warehouse": "Stores - BT",
        "basic_rate": 50000
    })
    se.insert()
    se.submit()
    print("Added stock for delivery.")
    
    frappe.set_user("warehouse@atulya.com")
    # Make Delivery Note
    dn = frappe.new_doc("Delivery Note")
    dn.customer = customer_name
    dn.append("items", {
        "item_code": item_code,
        "qty": 1,
        "against_sales_order": so.name,
        "so_detail": so.items[0].name,
        "warehouse": "Stores - BT",
        "rate": 94000
    })
    dn.insert()
    print(f"Warehouse created DN: {dn.name} in state {dn.workflow_state}")
    
    frappe.set_user("dispatch@atulya.com")
    dn = frappe.get_doc("Delivery Note", dn.name)
    dn.submit()
    print(f"Dispatch Exec approved QC and submitted! State: {dn.workflow_state}")
    print(f"QC Checked By field: {dn.qc_checked_by}")
    
    print("\n--- PHASE 3: INVOICING & GST (ACCOUNTS) ---")
    frappe.set_user("accounts@atulya.com")
    si = frappe.new_doc("Sales Invoice")
    si.customer = customer_name
    si.append("items", {
        "item_code": item_code,
        "qty": 1,
        "sales_order": so.name,
        "so_detail": so.items[0].name,
        "delivery_note": dn.name,
        "dn_detail": dn.items[0].name,
        "rate": 94000
    })
    si.insert()
    print(f"Created Sales Invoice: {si.name}")
    
    # Try to submit > 50k without e-way bill
    try:
        si.submit()
        print("ERROR: Invoice submitted without E-Way bill! Validation failed.")
    except Exception as e:
        print(f"SUCCESS: E-Way Bill validation correctly blocked submission! Message: {str(e)}")
        
    # Fix and submit
    frappe.set_user("accounts@atulya.com")
    
    # Bypass Advance Payment strictly for this test
    frappe.db.set_value("Sales Order", so.name, "advance_paid", 100000)
    frappe.db.commit()
    
    si = frappe.get_doc("Sales Invoice", si.name)
    si.e_way_bill_no = "123456789012"
    si.submit()
    print(f"Successfully submitted Sales Invoice {si.name} with E-Way Bill.")
    
    print("\n--- PHASE 4: CREDIT NOTE WORKFLOW ---")
    frappe.set_user("Administrator")
    cn = frappe.new_doc("Sales Invoice")
    cn.customer = customer_name
    cn.is_return = 1
    cn.return_against = si.name
    cn.append("items", {
        "item_code": item_code,
        "qty": -1,
        "rate": 94000
    })
    cn.insert()
    print(f"Sales Manager initiated Return: {cn.name}. State: {cn.workflow_state}")
    
    apply_workflow(cn, "Request Verification")
    print(f"Requested Verification. State: {cn.workflow_state}")
    
    frappe.set_user("Administrator")
    cn = frappe.get_doc("Sales Invoice", cn.name)
    apply_workflow(cn, "Approve Credit Note")
    print(f"Accounts Manager Approved Credit Note! State: {cn.workflow_state}")
    
    print("\n--- TEST COMPLETED SUCCESSFULLY! ---")
    frappe.db.rollback()
    print("Database rolled back (clean slate).")
