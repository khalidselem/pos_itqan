import json

def apply_tax_override(doc):
    # This simulates what we can do in the hook!
    items_with_tax = {"ITEM-VAT"} # Suppose this item has VAT
    item_codes = ["ITEM-VAT", "ITEM-NO-VAT"]
    
    # We don't even need to modify doc.taxes
    # We can just inject the JSON into item.item_tax_rate FOR non-VAT items IF doc.taxes exists!
    pass
