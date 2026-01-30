import frappe
from frappe import _
import json

@frappe.whitelist()
def get_tables():
    """Returns all tables with their current status and active order details."""
    # Check if 'orders' field exists (it may not if migrate hasn't been run)
    has_orders_field = frappe.db.has_column("POS Table", "orders")
    # Check if 'received_at' field exists
    has_received_at_field = frappe.db.has_column("POS Table", "received_at")
    
    fields = ["name", "table_name", "zone", "capacity", "status", "current_order", "current_customer", "notes"]
    
    if has_orders_field:
        fields.append("orders")
        
    if has_received_at_field:
        fields.append("received_at")
    
    tables = frappe.get_all("POS Table", 
        fields=fields,
        order_by="zone, table_name"
    )
    
    # Parse orders JSON for each table
    for table in tables:
        if has_orders_field and table.get("orders"):
            try:
                table["orders"] = json.loads(table["orders"])
            except (json.JSONDecodeError, TypeError):
                table["orders"] = []
        else:
            table["orders"] = []
    return tables

@frappe.whitelist()
def update_table_status(table, status, current_order=None, current_customer=None, clear_all_orders=False):
    """Updates table status and optionally links/unlinks an order/customer."""
    doc = frappe.get_doc("POS Table", table)
    doc.status = status
    doc.current_order = current_order
    doc.current_customer = current_customer
    
    # Save received_at timestamp when table becomes Occupied or Reserved
    # Only if the field exists in DB
    if frappe.db.has_column("POS Table", "received_at"):
        if status in ["Occupied", "Reserved"]:
            doc.received_at = frappe.utils.now()
        elif status == "Available":
            doc.received_at = None
    
    # Clear all orders if requested (e.g., after checkout)
    if clear_all_orders:
        doc.orders = json.dumps([])
    
    doc.save(ignore_permissions=True)
    return doc

@frappe.whitelist()
def add_order_to_table(table, draft_id, customer=None):
    """Adds a draft order ID to the table's orders list."""
    doc = frappe.get_doc("POS Table", table)
    
    # Parse existing orders
    orders = []
    if doc.orders:
        try:
            orders = json.loads(doc.orders)
        except (json.JSONDecodeError, TypeError):
            orders = []
    
    # Add new order if not already present
    if draft_id and draft_id not in orders:
        orders.append(draft_id)
    
    doc.orders = json.dumps(orders)
    doc.status = "Occupied"
    
    # Set current_order to first order (for backward compatibility)
    if orders and not doc.current_order:
        doc.current_order = orders[0]
    
    # Set customer if provided
    if customer:
        doc.current_customer = customer
    
    doc.save(ignore_permissions=True)
    return {"orders": orders, "status": doc.status}

@frappe.whitelist()
def remove_order_from_table(table, draft_id):
    """Removes a draft order ID from the table's orders list."""
    doc = frappe.get_doc("POS Table", table)
    
    # Parse existing orders
    orders = []
    if doc.orders:
        try:
            orders = json.loads(doc.orders)
        except (json.JSONDecodeError, TypeError):
            orders = []
    
    # Remove the order
    if draft_id in orders:
        orders.remove(draft_id)
    
    doc.orders = json.dumps(orders)
    
    # Update current_order
    if orders:
        doc.current_order = orders[0]
    else:
        doc.current_order = None
        doc.current_customer = None
        doc.status = "Available"
    
    doc.save(ignore_permissions=True)
    return {"orders": orders, "status": doc.status}

@frappe.whitelist()
def get_table_orders(table):
    """Returns all draft order IDs linked to a table."""
    doc = frappe.get_doc("POS Table", table)
    orders = []
    if doc.orders:
        try:
            orders = json.loads(doc.orders)
        except (json.JSONDecodeError, TypeError):
            orders = []
    return orders

@frappe.whitelist()
def get_zones():
    """Returns all available zones."""
    return frappe.get_all("POS Table Zone", fields=["name", "zone_name"])
