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
            "fieldname": "table_name",
            "label": _("Table"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "zone",
            "label": _("Zone"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "current_customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        },
        {
            "fieldname": "current_order",
            "label": _("Current Order"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "capacity",
            "label": _("Capacity"),
            "fieldtype": "Int",
            "width": 80
        },
        {
            "fieldname": "notes",
            "label": _("Notes"),
            "fieldtype": "Data",
            "width": 200
        },
    ]


def get_data(filters):
    # Check if Restaurant Table DocType exists
    if not frappe.db.exists("DocType", "Restaurant Table"):
        frappe.msgprint(_("Restaurant Table DocType not found. Please ensure the POS Tables module is installed."))
        return []
    
    conditions = []
    
    if filters.get("zone"):
        conditions.append(f"zone = '{frappe.db.escape(filters.get('zone'))}'")
    
    if filters.get("status"):
        conditions.append(f"status = '{frappe.db.escape(filters.get('status'))}'")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    try:
        tables = frappe.db.sql(f"""
            SELECT 
                table_name,
                zone,
                status,
                current_customer,
                current_order,
                capacity,
                notes
            FROM `tabRestaurant Table`
            WHERE {where_clause}
            ORDER BY zone, table_name
        """, as_dict=True)
        
        return tables
    except Exception as e:
        frappe.log_error(f"Table Details Report Error: {str(e)}")
        return []
