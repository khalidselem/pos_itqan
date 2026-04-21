import frappe
from frappe import _
import json

@frappe.whitelist()
def get_tables():
    """Returns all tables with their current status and active order details."""
    # Check if 'orders' field exists (it may not if migrate hasn't been run)
    has_orders_field = frappe.db.has_column("POS Table", "orders")
    
    fields = ["name", "table_name", "zone", "capacity", "status", "current_order", "current_customer", "notes", "received_at"]
    
    if has_orders_field:
        fields.append("orders")
    
    tables = frappe.get_all("POS Table", 
        fields=fields,
        order_by="zone, table_name"
    )
    
    # Parse orders JSON for each table
    for table in tables:
        if has_orders_field and table.get("orders"):
            try:
                orders = json.loads(table["orders"])
                valid_orders = []
                
                # Check each order's validity ("Self-healing")
                if orders:
                    for order_name in orders:
                        # Local drafts (from IndexedDB) start with "DRAFT-"
                        # These are always valid since they exist on the client
                        if order_name.startswith("DRAFT-"):
                            valid_orders.append(order_name)
                        elif frappe.db.exists("Sales Invoice", order_name):
                            # Backend Sales Invoice - only keep drafts (docstatus=0)
                            docstatus = frappe.db.get_value("Sales Invoice", order_name, "docstatus")
                            if docstatus == 0:
                                valid_orders.append(order_name)
                    
                    # If the list changed, update the table
                    if len(valid_orders) != len(orders):
                        # Update the DB immediately to "heal" the data
                        frappe.db.set_value("POS Table", table["name"], "orders", json.dumps(valid_orders))
                        # Also update current_order if it was removed
                        current_order = table.get("current_order")
                        if current_order and current_order not in valid_orders:
                            new_current = valid_orders[0] if valid_orders else None
                            frappe.db.set_value("POS Table", table["name"], "current_order", new_current)
                            table["current_order"] = new_current
                            
                            # If no orders left, clear status/customer if it was occupied
                            if not valid_orders and table["status"] == "Occupied":
                                frappe.db.set_value("POS Table", table["name"], "status", "Available")
                                frappe.db.set_value("POS Table", table["name"], "current_customer", None)
                                frappe.db.set_value("POS Table", table["name"], "received_at", None)
                                table["status"] = "Available"
                                table["current_customer"] = None
                                table["received_at"] = None
                
                table["orders"] = valid_orders
            except (json.JSONDecodeError, TypeError):
                table["orders"] = []
        else:
            table["orders"] = []
    return tables

@frappe.whitelist()
def update_table_status(table, status, current_order=None, current_customer=None, clear_all_orders=False, received_at=None, notes=None):
    """Updates table status and optionally links/unlinks an order/customer."""
    doc = frappe.get_doc("POS Table", table)
    doc.status = status
    doc.current_order = current_order
    doc.current_customer = current_customer
    
    # Save notes if provided
    if notes is not None:
        doc.notes = notes
    
    # Save received_at timestamp when table becomes Occupied or Reserved
    if status in ["Occupied", "Reserved"]:
        # Use provided time or current time
        doc.received_at = received_at or frappe.utils.now()
    elif status in ["Available", "Closed"]:
        doc.received_at = None
    
    # Clear all orders if requested (e.g., after checkout)
    if clear_all_orders:
        doc.orders = json.dumps([])
        doc.current_order = None
        doc.current_customer = None
        doc.received_at = None
    
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
    
    # Only set to Occupied if not already occupied (preserve existing status if orders existed)
    was_available = doc.status in ["Available", "Reserved"]
    doc.status = "Occupied"
    
    # Set received_at timestamp when table first becomes occupied
    if was_available or not doc.received_at:
        doc.received_at = frappe.utils.now()
    
    # Set current_order to first order (for backward compatibility)
    if orders and not doc.current_order:
        doc.current_order = orders[0]
    
    # Set customer if provided
    if customer:
        doc.current_customer = customer
    
    doc.save(ignore_permissions=True)
    return {"orders": orders, "status": doc.status, "received_at": doc.received_at}

@frappe.whitelist()
def remove_order_from_table(table, draft_id):
    """Removes a draft order ID from the table's orders list.
    
    Also handles the case where the order ID was renamed (e.g., from draft name 
    to submitted invoice name) by checking if the draft_id matches any order.
    """
    doc = frappe.get_doc("POS Table", table)
    
    # Parse existing orders
    orders = []
    if doc.orders:
        try:
            orders = json.loads(doc.orders)
        except (json.JSONDecodeError, TypeError):
            orders = []
    
    # Try to find and remove the order (handle both exact match and partial match)
    order_found = False
    if draft_id in orders:
        orders.remove(draft_id)
        order_found = True
    else:
        # Fallback: try to find an order that might have been renamed
        # This handles the case where draft was renamed on submission
        for order in orders[:]:  # Use slice copy to safely modify during iteration
            if order == draft_id or draft_id.startswith(order) or order.startswith(draft_id):
                orders.remove(order)
                order_found = True
                break
    
    doc.orders = json.dumps(orders)
    
    # Update current_order
    if orders:
        doc.current_order = orders[0]
    else:
        doc.current_order = None
        doc.current_customer = None
        doc.received_at = None  # Clear received timestamp when table is freed
        doc.status = "Available"
    
    doc.save(ignore_permissions=True)
    return {"orders": orders, "status": doc.status, "order_removed": order_found}

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
