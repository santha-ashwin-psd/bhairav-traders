frappe.ui.form.on('Pick List', {
    refresh: function(frm) {
        // Hide Sales Invoice option for Warehouse Manager to prevent skipping the Delivery Note step
        if (frappe.user.has_role("Warehouse Manager") && !frappe.user.has_role("System Manager")) {
            setTimeout(() => {
                frm.remove_custom_button('Sales Invoice', 'Create');
            }, 100);
        }
    }
});
