frappe.ready(function() {
	function setup_buttons() {
		// Wait until DOM is fully loaded and Frappe has rendered the form fields
		if ($('[data-fieldname="customer_approval_status"]').length === 0) {
			setTimeout(setup_buttons, 200);
			return;
		}

		// Prevent duplicate buttons
		if ($('#btn-approve-order').length > 0) {
			return;
		}

		let order_name = frappe.web_form.doc_name || window.location.pathname.split('/').pop();
		if (!order_name || order_name === 'new' || order_name === 'list' || order_name === 'customer-pending-approvals') {
			return;
		}

		// Extract status from the read-only DOM element
		let status_el = $('[data-fieldname="customer_approval_status"]');
		let status = status_el.find('.control-value').text().trim() || status_el.val() || status_el.text().trim();
		
		if (!status.includes("Pending")) {
			return;
		}

		// Prepend action buttons to the main wrapper
		let container = $('.web-form-wrapper');
		if (container.length === 0) container = $('.page_content, .page-content');
		
		container.prepend(`
			<div class="web-form-actions text-right" style="margin-bottom: 20px;">
				<button class="btn btn-success btn-sm" id="btn-approve-order">Approve Order</button>
				<button class="btn btn-danger btn-sm ml-2" id="btn-reject-order">Reject Order</button>
			</div>
		`);

		$('#btn-approve-order').on('click', function (e) {
			e.preventDefault();
			frappe.confirm('Are you sure you want to approve this order?', () => {
				frappe.call({
					method: 'bhairav_traders.portal_utils.approve_customer_order',
					args: {
						order_name: order_name
					},
					callback: function (r) {
						if (!r.exc) {
							frappe.msgprint('Order Approved Successfully');
							setTimeout(() => window.location.reload(), 1500);
						}
					}
				});
			});
		});

		$('#btn-reject-order').on('click', function (e) {
			e.preventDefault();
			frappe.prompt([
				{
					fieldname: 'reason',
					fieldtype: 'Small Text',
					label: 'Reason for Rejection',
					reqd: 1
				}
			],
				function (values) {
					frappe.call({
						method: 'bhairav_traders.portal_utils.reject_customer_order',
						args: {
							order_name: order_name,
							reason: values.reason
						},
						callback: function (r) {
							if (!r.exc) {
								frappe.msgprint('Order Rejected');
								setTimeout(() => window.location.reload(), 1500);
							}
						}
					});
				},
				'Reject Order',
				'Submit');
		});
	}

	setTimeout(setup_buttons, 500);
});