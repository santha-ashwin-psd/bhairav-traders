import frappe

def validate_sales_person(doc, method):
    """
    Automatically assign 'Salesman' role to the linked User when a Sales Person is created/updated.
    """
    if doc.user:
        user = frappe.get_doc("User", doc.user)
        has_salesman_role = any(d.role == "Salesman" for d in user.get("roles"))
        if not has_salesman_role:
            user.append("roles", {"role": "Salesman"})
            user.save(ignore_permissions=True)
            frappe.msgprint(f"Role 'Salesman' was automatically assigned to User {doc.user}.")

def before_validate_sales_person(doc, method):
    """
    Since the employee field is hidden/not needed, explicitly clear it 
    to prevent Frappe from auto-defaulting it to the logged-in user's employee ID 
    and throwing duplicate validation errors.
    """
    doc.employee = None

