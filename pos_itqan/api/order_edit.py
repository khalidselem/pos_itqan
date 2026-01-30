"""
Order Edit API - Permission checks for restaurant order editing
"""
import frappe
from frappe import _


@frappe.whitelist()
def can_edit_orders(pos_profile):
    """
    Check if the current user can edit previous restaurant orders.
    
    Returns:
        dict: { can_edit: bool, reason: str }
    """
    if not pos_profile:
        return {"can_edit": False, "reason": _("No POS Profile specified")}
    
    # Check if POS Settings exist for this profile
    settings = frappe.db.get_value(
        "POS Settings",
        {"pos_profile": pos_profile},
        ["allow_order_edit", "order_edit_roles"],
        as_dict=True
    )
    
    if not settings:
        return {"can_edit": False, "reason": _("POS Settings not found for this profile")}
    
    # Check if order editing is enabled
    if not settings.get("allow_order_edit"):
        return {"can_edit": False, "reason": _("Order editing is disabled")}
    
    # Check user roles
    order_edit_roles = settings.get("order_edit_roles", "").strip()
    
    # If no roles specified, allow all users
    if not order_edit_roles:
        return {"can_edit": True, "reason": _("All users can edit orders")}
    
    # Parse roles and check if user has any of them
    allowed_roles = [r.strip() for r in order_edit_roles.split(",") if r.strip()]
    user_roles = frappe.get_roles(frappe.session.user)
    
    for role in allowed_roles:
        if role in user_roles:
            return {"can_edit": True, "reason": _("User has {0} role").format(role)}
    
    return {"can_edit": False, "reason": _("User does not have permission to edit orders")}


@frappe.whitelist()
def get_order_edit_settings(pos_profile):
    """
    Get order edit settings for a POS Profile.
    
    Returns:
        dict: Order edit settings
    """
    if not pos_profile:
        return {"allow_order_edit": False, "order_edit_roles": ""}
    
    settings = frappe.db.get_value(
        "POS Settings",
        {"pos_profile": pos_profile},
        ["allow_order_edit", "order_edit_roles"],
        as_dict=True
    )
    
    return settings or {"allow_order_edit": False, "order_edit_roles": ""}
