frappe.ready(function() {
    // Only show buttons if it is an existing document view (not a list view)
    if (frappe.web_form && frappe.web_form.doc && frappe.web_form.doc.name) {
        
        // Add Accept Button
        frappe.web_form.add_button('Accept', () => {
            frappe.confirm('Are you sure you want to digitally Accept this quotation?', () => {
                frappe.call({
                    method: "bhairav_traders.portal_utils.accept_quotation",
                    args: { quotation_name: frappe.web_form.doc.name },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.msgprint("Quotation successfully accepted!");
                            setTimeout(() => window.location.reload(), 1500);
                        }
                    }
                });
            });
        }, 'btn-success');
        
        // Add Reject Button
        frappe.web_form.add_button('Reject', () => {
            frappe.prompt(
                {fieldtype: 'Data', fieldname: 'reason', label: 'Reason for rejection', reqd: 1},
                function(values) {
                    frappe.call({
                        method: "bhairav_traders.portal_utils.reject_quotation",
                        args: { quotation_name: frappe.web_form.doc.name, reason: values.reason },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.msgprint("Quotation marked as rejected.");
                                setTimeout(() => window.location.reload(), 1500);
                            }
                        }
                    });
                },
                'Reject Quotation',
                'Submit Rejection'
            );
        }, 'btn-danger');
    }
});