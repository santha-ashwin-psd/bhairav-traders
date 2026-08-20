frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        set_workflow_indicator(frm);
        
        // Hide the "Create -> Sales Invoice" button for Commercial users to prevent bypassing the workflow
        if (frappe.user.has_role("Commercial") && !frappe.user.has_role("System Manager")) {
            setTimeout(() => {
                frm.remove_custom_button('Sales Invoice', 'Create');
            }, 100);
        }

        // Hide unnecessary options for Warehouse Manager to keep the UI clean
        if (frappe.user.has_role("Warehouse Manager") && !frappe.user.has_role("System Manager")) {
            setTimeout(() => {
                frm.remove_custom_button('Material Request', 'Create');
                frm.remove_custom_button('Request for Raw Materials', 'Create');
                frm.remove_custom_button('Sales Invoice', 'Create');
            }, 100);
        }
    },
    workflow_state: function(frm) {
        set_workflow_indicator(frm);
    },
    customer: function(frm) {
        update_credit_details(frm);
    },
    company: function(frm) {
        update_credit_details(frm);
    },
    items_add: function(frm) {
        update_credit_details(frm);
    },
    items_remove: function(frm) {
        update_credit_details(frm);
    }
});

frappe.ui.form.on('Sales Order Item', {
    qty: function(frm) {
        update_credit_details(frm);
    },
    rate: function(frm) {
        update_credit_details(frm);
    },
    amount: function(frm) {
        update_credit_details(frm);
    }
});

// Map each workflow state to a color
const STATE_COLORS = {
    "Draft":                              "gray",
    "Pending Sales Manager Approval":     "orange",
    "Pending Regional Manager Approval":  "orange",
    "Pending Sales Head Approval":        "orange",
    "Pending Director Approval":          "orange",
    "Pending Commercial Credit Check":    "yellow",
    "Credit Hold":                        "red",
    "Pending Customer Approval":          "blue",
    "Customer Approved":                  "blue",
    "Packed":                             "purple",
    "Ready for Dispatch":                 "purple",
    "Dispatched":                         "green",
    "Invoiced":                           "green",
    "Completed":                          "green",
    "Rejected":                           "red"
};

function set_workflow_indicator(frm) {
    let state = frm.doc.workflow_state;
    if (!state) return;

    let color = STATE_COLORS[state] || "gray";
    frm.page.set_indicator(state, color);
}

function update_credit_details(frm) {
    if (!frm.doc.customer || !frm.doc.company) {
        frm.set_value("credit_exposure", 0);
        frm.set_value("available_credit", 0);
        return;
    }

    frappe.call({
        method: "bhairav_traders.credit_limit.get_customer_credit_details",
        args: {
            customer: frm.doc.customer,
            company: frm.doc.company
        },
        callback: function(r) {
            if (r.message) {
                let credit_limit = flt(r.message.credit_limit);
                let total_outstanding = flt(r.message.total_outstanding);
                let grand_total = flt(frm.doc.grand_total) || 0;

                let total_exposure = total_outstanding + grand_total;
                
                frm.set_value("credit_exposure", total_exposure);
                
                if (credit_limit > 0) {
                    let available_credit = credit_limit - total_exposure;
                    frm.set_value("available_credit", available_credit > 0 ? available_credit : 0);
                } else {
                    frm.set_value("available_credit", 0);
                }
            }
        }
    });
}
