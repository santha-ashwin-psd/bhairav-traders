frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        // Hide unnecessary options in the Create dropdown to keep UI clean for Accounts team
        if ((frappe.user.has_role("Accounts Executive") || frappe.user.has_role("Accounts User") || frappe.user.has_role("Accounts Manager")) && !frappe.user.has_role("System Manager")) {
            setTimeout(() => {
                frm.remove_custom_button('Delivery Note', 'Create');
                frm.remove_custom_button('Invoice Discounting', 'Create');
                frm.remove_custom_button('Dunning', 'Create');
                frm.remove_custom_button('Maintenance Schedule', 'Create');
            }, 100);
        }
    }
});
