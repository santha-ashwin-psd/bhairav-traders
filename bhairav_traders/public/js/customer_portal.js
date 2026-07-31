frappe.provide('frappe.ui');

frappe.ui.portal_confirm = function(title, message, on_yes) {
    let modal_id = "globalPortalConfirmModal";
    if (!$('#' + modal_id).length) {
        let modal_html = `
            <div class="modal fade" id="${modal_id}" tabindex="-1" role="dialog" aria-hidden="true">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="${modal_id}_title">Confirmation Required</h5>
                        </div>
                        <div class="modal-body">
                            <p id="${modal_id}_msg"></p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-default btn-secondary btn-sm" onclick="$('#${modal_id}').modal('hide');">No</button>
                            <button type="button" class="btn btn-primary btn-sm" id="btn-global-confirm-yes">Yes</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        $('body').append(modal_html);
    }
    
    $('#' + modal_id + '_title').text(title || "Confirmation Required");
    $('#' + modal_id + '_msg').html(message);
    
    // Unbind previous handlers
    $('#btn-global-confirm-yes').off('click').on('click', function() {
        $('#' + modal_id).modal('hide');
        if (on_yes) {
            setTimeout(() => {
                on_yes();
            }, 300);
        }
    });
    
    $('#' + modal_id).modal('show');
};
