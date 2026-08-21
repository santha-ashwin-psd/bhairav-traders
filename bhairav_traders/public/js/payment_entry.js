frappe.ui.form.on('Payment Entry', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) {
            let has_so = false;
            let so_name = "";
            if (frm.doc.references) {
                for (let i=0; i<frm.doc.references.length; i++) {
                    if (frm.doc.references[i].reference_doctype === "Sales Order") {
                        has_so = true;
                        so_name = frm.doc.references[i].reference_name;
                        break;
                    }
                }
            }
            if (has_so && so_name) {
                frm.add_custom_button('Sales Invoice', () => {
                    frappe.model.open_mapped_doc({
                        method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
                        frm: frm,
                        source_name: so_name
                    });
                }, 'Create');
            }
        }
    }
});
