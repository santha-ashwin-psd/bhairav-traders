frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        // Hide unnecessary options in the Create dropdown to keep UI clean for Accounts team
        if ((frappe.user.has_role("Accounts Executive") || frappe.user.has_role("Finance Manager")) && !frappe.user.has_role("System Manager")) {
            setTimeout(() => {
                frm.remove_custom_button('Delivery Note', 'Create');
                frm.remove_custom_button('Invoice Discounting', 'Create');
                frm.remove_custom_button('Dunning', 'Create');
                frm.remove_custom_button('Maintenance Schedule', 'Create');
            }, 100);
        }

        // Only Finance Manager (Finance Manager) or Director can check the override box
        if (!frappe.user.has_role("Finance Manager") && !frappe.user.has_role("Finance Manager") && !frappe.user.has_role("Director") && !frappe.user.has_role("System Manager")) {
            frm.set_df_property('approved_during_lock', 'read_only', 1);
        }

        // Show Create Payment shortcut if Advance Payment is needed
        if (frm.doc.docstatus === 0 && !frm.is_new()) {
            frappe.call({
                method: "bhairav_traders.portal_utils.check_advance_payment_needed_for_invoice",
                args: { invoice_name: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        setTimeout(() => {
                            frm.add_custom_button(__('Payment'), () => {
                                frappe.call({
                                    method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
                                    args: {
                                        dt: "Sales Order",
                                        dn: r.message
                                    },
                                    callback: function(resp) {
                                        var doc = frappe.model.sync(resp.message);
                                        frappe.set_route("Form", doc[0].doctype, doc[0].name);
                                    }
                                });
                            }, 'Create');
                        }, 200);
                    }
                }
            });
        }
    }
});
