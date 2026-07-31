frappe.ready(function () {
    let has_credit = true;
    let customer_name = "";

    frappe.call({
        method: "bhairav_traders.portal_utils.get_customer_credit_limit",
        callback: function (r) {
            if (r.message === 0) {
                has_credit = false;
            }
        }
    });

    frappe.call({
        method: "bhairav_traders.portal_utils.get_logged_in_customer_details",
        callback: function (r) {
            if (r.message && r.message.customer) {
                frappe.web_form.set_value('customer', r.message.customer);
                customer_name = r.message.customer_name || r.message.customer;
            }
        }
    });

    let confirm_shown = false;

    frappe.web_form.validate = () => {
        if (!has_credit && !confirm_shown) {
            // Temporarily disable frappe.msgprint to completely swallow the "Validation Error" modal
            let _original_msgprint = frappe.msgprint;
            frappe.msgprint = function() {};
            
            // Restore msgprint after Frappe finishes its internal validation routines
            setTimeout(() => {
                frappe.msgprint = _original_msgprint;
            }, 500);

            let msg = `Notice: No credit limit is issued for customer '${customer_name}'. Order will be executed on advance payment.`;
            
            frappe.ui.portal_confirm("Confirmation Required", msg, function() {
                confirm_shown = true;
                $('.web-form-actions .btn-primary').click();
            });

            // Hide the default "Couldn't save" error that pops up when returning false
            setTimeout(() => {
                if (frappe.hide_msgprint) {
                    frappe.hide_msgprint();
                } else if ($('.msgprint-dialog').length) {
                    $('.msgprint-dialog').modal('hide');
                }
            }, 10);
            return false;
        }
        return true;
    };

    frappe.web_form.set_query("item_code", "items", function (doc, cdt, cdn) {
        return {
            query: "bhairav_traders.portal_utils.get_item_search_results"
        };
    });

    // Hook into the grid row's item_code field change
    // This fires when user picks an item from the dropdown inside the row form
    $(document).on('change', 'input[data-fieldname="item_code"]', function () {
        setTimeout(apply_rates, 500);
    });

    // Also poll every 1s as a safety net
    let fetching = {};

    function apply_rates() {
        let items_field = frappe.web_form.get_field('items');
        if (!items_field || !items_field.grid) return;

        let rows = items_field.grid.get_data();
        if (!rows || !rows.length) return;

        rows.forEach(function (row) {
            if (!row.item_code) return;
            if (row.rate > 0) {
                // rate already set, just sync amount
                let expected_amount = flt(row.rate) * flt(row.qty || 1);
                if (flt(row.amount) !== expected_amount) {
                    frappe.model.set_value(row.doctype, row.name, 'amount', expected_amount);
                    items_field.grid.refresh();
                }
                return;
            }

            // Rate not set — fetch it
            if (fetching[row.name]) return;
            fetching[row.name] = true;

            frappe.call({
                method: 'bhairav_traders.portal_utils.get_item_rate',
                args: { item_code: row.item_code },
                callback: function (r) {
                    delete fetching[row.name];
                    if (!r.message || flt(r.message) === 0) return;

                    let rate = flt(r.message);
                    let qty = flt(row.qty) || 1;

                    frappe.model.set_value(row.doctype, row.name, 'rate', rate);
                    frappe.model.set_value(row.doctype, row.name, 'qty', qty);
                    frappe.model.set_value(row.doctype, row.name, 'amount', rate * qty);

                    // Also update directly on the row object for display
                    row.rate = rate;
                    row.qty = qty;
                    row.amount = rate * qty;

                    items_field.grid.refresh();
                    // If the child row dialog is open, refresh it too
                    if (items_field.grid.open_grid_row) {
                        items_field.grid.open_grid_row.row_form && items_field.grid.open_grid_row.row_form.refresh();
                    }
                }
            });
        });
    }

    setInterval(apply_rates, 1000);
});
