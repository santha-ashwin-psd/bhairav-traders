import frappe

def change_comm_type(doc, method):
    if doc.communication_type == "Automated Message" and doc.communication_medium == "Email":
        doc.communication_type = "Communication"
