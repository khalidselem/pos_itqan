frappe.ui.form.on('Sales Invoice', {
    refresh: function (frm) {
        if (frm.doc.docstatus === 0) {
            // Make restaurant fields read-only
            const restaurant_fields = [
                'custom_pos_table',
                'custom_table_notes',
                'custom_table_received_at',
                'custom_customer_count',
                'custom_table_zone'
            ];

            restaurant_fields.forEach(field => {
                if (frm.fields_dict[field]) {
                    frm.set_df_property(field, 'read_only', 1);
                }
            });

            // Explicitly show set_warehouse if pos_profile is set
            if (frm.doc.pos_profile) {
                frm.toggle_display('set_warehouse', true);
            }
        }
    },

    pos_profile: function (frm) {
        if (frm.doc.pos_profile) {
            // Ensure Update Stock is checked, as set_warehouse depends on it
            if (frm.fields_dict['update_stock']) {
                frm.set_value('update_stock', 1);
            }

            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'POS Profile',
                    filters: { name: frm.doc.pos_profile },
                    fieldname: 'warehouse'
                },
                callback: function (r) {
                    if (r && r.message && r.message.warehouse) {
                        frm.set_value('set_warehouse', r.message.warehouse);

                        // Aggressively ensure visibility
                        if (frm.fields_dict['set_warehouse']) {
                            frm.set_df_property('set_warehouse', 'hidden', 0);
                            frm.toggle_display('set_warehouse', true);
                            frm.refresh_field('set_warehouse');
                        } else {
                            console.warn("Field 'set_warehouse' not found in Sales Invoice form.");
                        }
                    }
                }
            });
        }
    }
});
