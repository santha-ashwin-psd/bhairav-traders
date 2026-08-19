import frappe

def execute():
    # 1. Remove standard roles from the 10 custom users
    users_to_clean = [
        "sales_exec@atulya.com",
        "sales_manager@atulya.com",
        "regional_manager@atulya.com",
        "sales_head@atulya.com",
        "director@atulya.com",
        "commercial@atulya.com",
        "warehouse@atulya.com",
        "dispatch@atulya.com",
        "accounts@atulya.com",
        "finance@atulya.com"
    ]
    
    for email in users_to_clean:
        if frappe.db.exists("User", email):
            user = frappe.get_doc("User", email)
            roles_to_keep = [r for r in user.get("roles") if r.role not in ["Sales User", "Accounts User", "Stock User"]]
            user.set("roles", roles_to_keep)
            user.save(ignore_permissions=True)
            print(f"Cleaned broad roles for {email}")

    # 2. Define Custom Permissions
    # Format: { Doctype: { Role: { "read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0 } } }
    
    perm_map = {
        "Sales Order": {
            "Sales Executive": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
            "Sales Manager": {"read": 1, "write": 1, "create": 0, "submit": 1, "cancel": 1, "amend": 1},
            "Regional Manager": {"read": 1, "write": 1, "create": 0, "submit": 1, "cancel": 1, "amend": 1},
            "Sales Head": {"read": 1, "write": 1, "create": 0, "submit": 1, "cancel": 1, "amend": 1},
            "Director": {"read": 1, "write": 1, "create": 0, "submit": 1, "cancel": 1, "amend": 1},
            "Commercial": {"read": 1, "write": 1, "create": 0, "submit": 1, "cancel": 1, "amend": 1},
            "Warehouse Manager": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
        },
        "Customer": {
            "Sales Executive": {"read": 1, "write": 1, "create": 1, "submit": 0, "cancel": 0, "amend": 0},
            "Sales Manager": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Regional Manager": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Sales Head": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Director": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Commercial": {"read": 1, "write": 1, "create": 1, "submit": 0, "cancel": 0, "amend": 0},
            "Accounts Executive": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Finance Manager": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
        },
        "Item": {
            "Sales Executive": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Sales Manager": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Regional Manager": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Sales Head": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Director": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Commercial": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Warehouse Manager": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Dispatch Executive": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
            "Accounts Executive": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
        },
        "Delivery Note": {
            "Warehouse Manager": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
            "Dispatch Executive": {"read": 1, "write": 1, "create": 0, "submit": 1, "cancel": 0, "amend": 0},
            "Accounts Executive": {"read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0},
        },
        "Stock Entry": {
            "Warehouse Manager": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
        },
        "Pick List": {
            "Warehouse Manager": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
        },
        "Sales Invoice": {
            "Accounts Executive": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
            "Finance Manager": {"read": 1, "write": 1, "create": 0, "submit": 1, "cancel": 1, "amend": 1},
            "Sales Manager": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
        },
        "Payment Entry": {
            "Accounts Executive": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
            "Finance Manager": {"read": 1, "write": 1, "create": 0, "submit": 1, "cancel": 1, "amend": 1},
        }
    }

    for doctype, role_perms in perm_map.items():
        for role, perms in role_perms.items():
            existing = frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": role})
            if existing:
                perm_doc = frappe.get_doc("Custom DocPerm", existing)
                for k, v in perms.items():
                    perm_doc.set(k, v)
                perm_doc.save(ignore_permissions=True)
            else:
                perm_doc = frappe.get_doc({
                    "doctype": "Custom DocPerm",
                    "parent": doctype,
                    "parenttype": "DocType",
                    "parentfield": "permissions",
                    "role": role,
                    "read": perms.get("read", 0),
                    "write": perms.get("write", 0),
                    "create": perms.get("create", 0),
                    "submit": perms.get("submit", 0),
                    "cancel": perms.get("cancel", 0),
                    "amend": perms.get("amend", 0)
                })
                perm_doc.insert(ignore_permissions=True)
            
            print(f"Set permissions for {role} on {doctype}")
        
        # Clear cache for doctype
        frappe.clear_cache(doctype=doctype)

    frappe.db.commit()
    print("All permissions set and cache cleared.")
