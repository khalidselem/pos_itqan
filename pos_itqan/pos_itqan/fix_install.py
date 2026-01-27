import frappe

def remove_invalid_search_field():
    try:
        doctype = "Sales Invoice Item"
        if not frappe.db.exists("DocType", doctype):
            print(f"DocType {doctype} not found.")
            return

        doc = frappe.get_doc("DocType", doctype)
        search_fields = (doc.search_fields or "").split(",")
        search_fields = [f.strip() for f in search_fields if f.strip()]
        
        if "item_name_arabic" in search_fields:
            print(f"Removing invalid search field 'item_name_arabic' from {doctype}...")
            search_fields.remove("item_name_arabic")
            doc.search_fields = ", ".join(search_fields)
            doc.save()
            frappe.db.commit()
            print("Successfully removed invalid search field.")
        else:
            print(f"'item_name_arabic' not found in search fields of {doctype}.")
            
    except Exception as e:
        frappe.log_error(f"Error in remove_invalid_search_field: {str(e)}")
        print(f"Error: {str(e)}")
