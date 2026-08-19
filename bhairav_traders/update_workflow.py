import frappe
import json

def run():
    frappe.set_user("Administrator")
    
    # 1. Create Workflow States
    states = ["Pending Regional Manager", "Pending Head Sales", "Pending Commercial Approval"]
    for s in states:
        if not frappe.db.exists("Workflow State", s):
            frappe.get_doc({
                "doctype": "Workflow State",
                "workflow_state_name": s
            }).insert(ignore_permissions=True)
            
    wf = frappe.get_doc("Workflow", "Atulya Sales Order Workflow")
    wf.workflow_name = "Atulya Sales Order Workflow"
    
    # Update states in Workflow
    current_states = [s.state for s in wf.get("states")]
    
    if "Pending Regional Manager" not in current_states:
        wf.append("states", {
            "state": "Pending Regional Manager",
            "allow_edit": "Regional Manager", 
            "doc_status": "0",
            "send_email": 1
        })
        
    if "Pending Head Sales" not in current_states:
        wf.append("states", {
            "state": "Pending Head Sales",
            "allow_edit": "Sales Head",
            "doc_status": "0",
            "send_email": 1
        })
        
    if "Pending Commercial Approval" not in current_states:
        wf.append("states", {
            "state": "Pending Commercial Approval",
            "allow_edit": "Commercial", 
            "doc_status": "0",
            "send_email": 1
        })

    # Clear old Draft transitions
    wf.set("transitions", [t for t in wf.get("transitions") if t.state != "Draft"])
    
    # Add new transitions from PDF matrix
    # 0-2% -> Auto approve to Pending Customer Approval
    wf.append("transitions", {
        "state": "Draft",
        "action": "Submit for approval",
        "next_state": "Pending Customer Approval",
        "allowed": "Salesman",
        "condition": "doc.additional_discount_percentage <= 2"
    })
    
    # 2-5% -> Sales Manager
    wf.append("transitions", {
        "state": "Draft",
        "action": "Submit for approval",
        "next_state": "Pending Sales Manager",
        "allowed": "Salesman",
        "condition": "doc.additional_discount_percentage > 2 and doc.additional_discount_percentage <= 5"
    })
    
    # 5-8% -> Regional Manager
    wf.append("transitions", {
        "state": "Draft",
        "action": "Submit for approval",
        "next_state": "Pending Regional Manager",
        "allowed": "Salesman",
        "condition": "doc.additional_discount_percentage > 5 and doc.additional_discount_percentage <= 8"
    })
    
    # 8-12% -> Head Sales
    wf.append("transitions", {
        "state": "Draft",
        "action": "Submit for approval",
        "next_state": "Pending Head Sales",
        "allowed": "Salesman",
        "condition": "doc.additional_discount_percentage > 8 and doc.additional_discount_percentage <= 12"
    })
    
    # 12-15% -> Director
    wf.append("transitions", {
        "state": "Draft",
        "action": "Submit for approval",
        "next_state": "Pending Director",
        "allowed": "Salesman",
        "condition": "doc.additional_discount_percentage > 12 and doc.additional_discount_percentage <= 15"
    })
    
    # >15% -> Director + Commercial
    wf.append("transitions", {
        "state": "Draft",
        "action": "Submit for approval",
        "next_state": "Pending Commercial Approval",
        "allowed": "Salesman",
        "condition": "doc.additional_discount_percentage > 15"
    })
    
    def add_approval_path(state, allowed_role):
        transitions = wf.get("transitions")
        has_approve = any(t.state == state and t.action == "Approve" for t in transitions)
        if not has_approve:
            wf.append("transitions", {
                "state": state,
                "action": "Approve",
                "next_state": "Pending Customer Approval",
                "allowed": allowed_role
            })
            wf.append("transitions", {
                "state": state,
                "action": "Reject",
                "next_state": "Rejected",
                "allowed": allowed_role
            })

    add_approval_path("Pending Regional Manager", "Regional Manager")
    add_approval_path("Pending Head Sales", "Sales Head")
    add_approval_path("Pending Commercial Approval", "Commercial")
    
    # Final step: Customer Approval
    transitions = wf.get("transitions")
    if not any(t.state == "Pending Customer Approval" and t.action == "Approve" for t in transitions):
        wf.append("transitions", {
            "state": "Pending Customer Approval",
            "action": "Approve",
            "next_state": "Approved",
            "allowed": "Customer"
        })
        wf.append("transitions", {
            "state": "Pending Customer Approval",
            "action": "Reject",
            "next_state": "Rejected",
            "allowed": "Customer"
        })
    
    wf.save(ignore_permissions=True)
    frappe.db.commit()
    print("Workflow updated successfully!")

