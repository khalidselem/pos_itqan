# Copyright (c) 2025, ITQAN LLC and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "order_name",
            "label": _("Order"),
            "fieldtype": "Link",
            "options": "POS Draft Order",
            "width": 150
        },
        {
            "fieldname": "table_name",
            "label": _("Table"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        },
        {
            "fieldname": "original_total",
            "label": _("Original Total"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "current_total",
            "label": _("Current Total"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "edit_count",
            "label": _("Edit Count"),
            "fieldtype": "Int",
            "width": 80
        },
        {
            "fieldname": "last_edited_at",
            "label": _("Last Edited"),
            "fieldtype": "Datetime",
            "width": 160
        },
        {
            "fieldname": "last_edited_by",
            "label": _("Edited By"),
            "fieldtype": "Link",
            "options": "User",
            "width": 150
        },
    ]


def get_data(filters):
    # Check if POS Draft Order DocType exists
    if not frappe.db.exists("DocType", "POS Draft Order"):
        frappe.msgprint(_("POS Draft Order DocType not found. Please ensure the POS module is properly installed."))
        return []
    
    conditions = []
    
    # Check if is_edited field exists
    try:
        meta = frappe.get_meta("POS Draft Order")
        if not meta.has_field("is_edited"):
            frappe.msgprint(_("The 'is_edited' field is not available in POS Draft Order."))
            return []
        conditions.append("is_edited = 1")
    except Exception:
        return []
    
    if filters.get("from_date"):
        conditions.append(f"creation >= '{frappe.db.escape(filters.get('from_date'))}'")
    
    if filters.get("to_date"):
        conditions.append(f"creation <= '{frappe.db.escape(filters.get('to_date'))} 23:59:59'")
    
    where_clause = " AND ".join(conditions)
    
    try:
        orders = frappe.db.sql(f"""
            SELECT 
                name as order_name,
                table_name,
                customer,
                original_total,
                grand_total as current_total,
                edit_count,
                last_edited_at,
                last_edited_by
            FROM `tabPOS Draft Order`
            WHERE {where_clause}
            ORDER BY last_edited_at DESC
        """, as_dict=True)
        
        return orders
    except Exception as e:
        frappe.log_error(f"Order Edits Report Error: {str(e)}")
        return []
