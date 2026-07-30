import frappe

def after_install():
    print("Setting up website and navbar logo configuration...")
    try:
        # 1. Update Website Settings
        ws = frappe.get_doc("Website Settings")
        ws.app_logo = "/assets/bhairav_traders/logo.png"
        ws.banner_image = "/assets/bhairav_traders/logo.png"
        ws.brand_html = '<div class="d-flex align-items-center"><img src="/assets/bhairav_traders/logo.png" style="max-height: 40px; margin-right: 10px;" alt="Bhairav Traders Logo"><span style="font-weight: 700; font-size: 1.25rem; letter-spacing: -0.02em; color: var(--text-color);">Bhairav Traders</span></div>'
        ws.save(ignore_permissions=True)
        print("Website Settings logo configured successfully.")

        # 2. Update Navbar Settings
        ns = frappe.get_doc("Navbar Settings")
        ns.app_logo = "/assets/bhairav_traders/logo.png"
        ns.save(ignore_permissions=True)
        print("Navbar Settings logo configured successfully.")

        # Commit DB changes and clear cache
        frappe.db.commit()
        frappe.clear_cache()
        print("Logo settings successfully committed and site cache cleared.")
    except Exception as e:
        print(f"Failed to auto-configure logo during installation: {e}")
