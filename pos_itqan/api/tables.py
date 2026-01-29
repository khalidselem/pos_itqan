import frappe
from frappe import _

@frappe.whitelist()
def get_tables():
    """Returns all tables with their current status and active order details."""
    tables = frappe.get_all("POS Table", 
        fields=["name", "table_name", "zone", "capacity", "status", "current_order", "current_customer", "notes"],
        order_by="zone, table_name"
    )
    return tables

@frappe.whitelist()
def update_table_status(table, status, current_order=None, current_customer=None):
    """Updates table status and optionally links/unlinks an order/customer."""
    doc = frappe.get_doc("POS Table", table)
    doc.status = status
    doc.current_order = current_order
    doc.current_customer = current_customer
    doc.save(ignore_permissions=True)
    return doc

@frappe.whitelist()
def get_zones():
    """Returns all available zones."""
    return frappe.get_all("POS Table Zone", fields=["name", "zone_name"])
