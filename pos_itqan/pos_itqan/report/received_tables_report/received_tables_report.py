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
        conditions.append(f"si.posting_date >= '{frappe.db.escape(filters.get('from_date'))}'")
    
    if filters.get("to_date"):
        conditions.append(f"si.posting_date <= '{frappe.db.escape(filters.get('to_date'))}'")
    
    where_clause = " AND ".join(conditions)
    
    # Check if custom_table field exists on Sales Invoice
    try:
        meta = frappe.get_meta("Sales Invoice")
        has_custom_table = meta.has_field("custom_table")
    except Exception:
        has_custom_table = False
    
    try:
        if has_custom_table:
            # Query with table info
            invoices = frappe.db.sql(f"""
                SELECT 
                    si.custom_table as table_name,
                    si.customer,
                    si.name as invoice,
                    si.grand_total,
                    si.posting_date,
                    si.posting_time,
                    si.status
                FROM `tabSales Invoice` si
                WHERE {where_clause}
                    AND si.custom_table IS NOT NULL
                    AND si.custom_table != ''
                ORDER BY si.posting_date DESC, si.posting_time DESC
            """, as_dict=True)
        else:
            # Query without table info - just show POS invoices
            invoices = frappe.db.sql(f"""
                SELECT 
                    '' as table_name,
                    si.customer,
                    si.name as invoice,
                    si.grand_total,
                    si.posting_date,
                    si.posting_time,
                    si.status
                FROM `tabSales Invoice` si
                WHERE {where_clause}
                ORDER BY si.posting_date DESC, si.posting_time DESC
            """, as_dict=True)
        
        return invoices
    except Exception as e:
        frappe.log_error(f"Received Tables Report Error: {str(e)}")
        return []
