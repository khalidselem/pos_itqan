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
            "fieldname": "customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        },
        {
            "fieldname": "invoice",
            "label": _("Invoice"),
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 150
        },
        {
            "fieldname": "grand_total",
            "label": _("Total"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "posting_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "posting_time",
            "label": _("Time"),
            "fieldtype": "Time",
            "width": 80
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        },
    ]


def get_data(filters):
    conditions = ["si.is_pos = 1", "si.docstatus = 1"]
    
    if filters.get("from_date"):
        conditions.append(f"si.posting_date >= '{filters.get('from_date')}'")
    
    if filters.get("to_date"):
        conditions.append(f"si.posting_date <= '{filters.get('to_date')}'")
    
    if filters.get("zone"):
        conditions.append(f"rt.zone = '{filters.get('zone')}'")
    
    where_clause = " AND ".join(conditions)
    
    # Get invoices that have table info
    invoices = frappe.db.sql(f"""
        SELECT 
            rt.table_name,
            rt.zone,
            si.customer,
            si.name as invoice,
            si.grand_total,
            si.posting_date,
            si.posting_time,
            si.status
        FROM `tabSales Invoice` si
        LEFT JOIN `tabRestaurant Table` rt ON si.custom_table = rt.name
        WHERE {where_clause}
            AND si.custom_table IS NOT NULL
            AND si.custom_table != ''
        ORDER BY si.posting_date DESC, si.posting_time DESC
    """, as_dict=True)
    
    return invoices
