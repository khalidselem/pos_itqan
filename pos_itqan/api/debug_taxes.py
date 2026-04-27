import frappe

def execute():
    templates = frappe.get_all("Item Tax Template", fields=["name", "company"])
    print("ALL TEMPLATES:", templates)
    
    item_taxes = frappe.get_all("Item Tax", filters={"parent": "SKU-0024"}, fields=["parent", "item_tax_template", "tax_category"])
    print("ITEM TAXES FOR SKU-0024:", item_taxes)
