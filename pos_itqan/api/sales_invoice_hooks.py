# Copyright (c) 2025, ITQAN LLC (info@itqan-kw.net, itqan-kw.com) and contributors
# For license information, please see license.txt

"""
Sales Invoice Hooks
Event handlers for Sales Invoice document events
"""

import frappe
from frappe import _
from frappe.utils import cint


def validate(doc, method=None):
	"""
	Validate hook for Sales Invoice.
	Apply tax inclusive settings based on POS Profile configuration.
	Auto-assign loyalty program to customer if enabled.

	Args:
		doc: Sales Invoice document
		method: Hook method name (unused)
	"""
	auto_assign_loyalty_program_on_invoice(doc)
	set_source_warehouse_from_pos_profile(doc)

def before_validate(doc, method=None):
	"""
	Runs BEFORE standard Frappe validation.
	Dynamically sets `item_tax_rate` to 0% for items that do not have a VAT template.
	This flawlessly informs ERPNext's standard calculated_taxes_and_totals logic
	to completely ignore these items for VAT, preserving all base and rounding math natively.
	"""
	apply_tax_inclusive(doc)

	if not doc.is_pos or not doc.get("taxes"):
		return
		
	try:
		import json
		import frappe
		
		item_codes = [item.item_code for item in doc.get("items") if item.item_code]
		if not item_codes:
			return
			
		# 1. Check child table 'Item Tax' (Explicitly for Items)
		tax_results = frappe.db.sql(
			"SELECT DISTINCT parent FROM `tabItem Tax` WHERE parent IN %s AND parenttype = 'Item'",
			(tuple(item_codes),),
		)
		items_with_tax = {row[0] for row in tax_results}
		
		# 2. Check Item master to get their Item Groups
		item_details = frappe.get_all(
			"Item",
			filters={"name": ["in", item_codes]},
			fields=["name", "item_group"]
		)
		
		item_to_group = {}
		for row in item_details:
			if row.get("item_group"):
				item_to_group[row["name"]] = row["item_group"]
				
		# 3. Check Item Group templates
		if item_to_group:
			groups = list(set(item_to_group.values()))
			group_templates = frappe.get_all(
				"Item Tax",
				filters={"parent": ["in", groups], "parenttype": "Item Group"},
				fields=["parent"]
			)
			groups_with_tax = {row["parent"] for row in group_templates}
			
			for item_code, group_name in item_to_group.items():
				if group_name in groups_with_tax:
					items_with_tax.add(item_code)
		
		# If the entire invoice has NO VAT items, wipe taxes completely.
		has_any_vat_item = any(item.item_code in items_with_tax for item in doc.get("items"))
		if not has_any_vat_item:
			doc.taxes_and_charges = None
			doc.set("taxes", [])
			return

		# Fetch the upcoming tax accounts proactively.
		# `doc.taxes` is usually empty this early in the lifecycle before Frappe's set_missing_values.
		pending_tax_accounts = []
		if doc.taxes_and_charges:
			template_taxes = frappe.db.get_all(
				"Sales Taxes and Charges",
				filters={"parent": doc.taxes_and_charges},
				fields=["account_head"]
			)
			pending_tax_accounts = [t.account_head for t in template_taxes if t.account_head]
		else:
			pending_tax_accounts = [t.account_head for t in doc.get("taxes") if t.account_head]

		frappe.log_error(f"tax_inclusive: {doc.get('tax_inclusive')}, items_with_tax: {items_with_tax}, pending_tax_accounts: {pending_tax_accounts}", "POS Debug Before")

		if not pending_tax_accounts:
			return

		# Otherwise, inject 0% on Non-VAT rows
		for item in doc.get("items"):
			is_taxable = item.item_code in items_with_tax
			frappe.log_error(f"Processing Item: {item.item_code}, Is Taxable: {is_taxable}", "POS Debug Item")
			
			if not is_taxable:
				current_overrides = {}
				if item.item_tax_rate:
					try:
						current_overrides = json.loads(item.item_tax_rate)
					except Exception:
						pass
				
				has_changes = False
				for account_head in pending_tax_accounts:
					if account_head and account_head not in current_overrides:
						current_overrides[account_head] = 0
						has_changes = True
				
				if has_changes:
					item.item_tax_rate = json.dumps(current_overrides)
					frappe.log_error(f"Injected 0% for {item.item_code}: {item.item_tax_rate}", "POS Debug Injected")
					
	except Exception as e:
		frappe.log_error(f"Error in VAT Override Hook: {e}\n{frappe.get_traceback()}", "POS VAT Override Error")


def apply_tax_inclusive(doc):
	"""
	Mark taxes as inclusive based on POS Profile setting.

	This function reads the tax_inclusive setting from POS Settings
	and applies it to all taxes in the invoice (except Actual charge type).

	Args:
		doc: Sales Invoice document
	"""
	if not doc.pos_profile:
		return

	try:
		# Get POS Settings for this profile
		pos_settings = frappe.db.get_value(
			"POS Settings",
			{"pos_profile": doc.pos_profile},
			["tax_inclusive"],
			as_dict=True
		)
		tax_inclusive = pos_settings.get("tax_inclusive", 0) if pos_settings else 0
	except Exception:
		tax_inclusive = 0

	has_changes = False
	for tax in doc.get("taxes", []):
		# Skip Actual charge type - these can't be inclusive
		if tax.charge_type == "Actual":
			if tax.included_in_print_rate:
				tax.included_in_print_rate = 0
				has_changes = True
			continue

		# Apply tax inclusive setting
		if tax_inclusive and not tax.included_in_print_rate:
			tax.included_in_print_rate = 1
			has_changes = True
		elif not tax_inclusive and tax.included_in_print_rate:
			tax.included_in_print_rate = 0
			has_changes = True

	# Recalculate if we made changes
	if has_changes:
		doc.calculate_taxes_and_totals()


def auto_assign_loyalty_program_on_invoice(doc):
	"""
	Auto-assign loyalty program to customer if loyalty is enabled in POS Settings
	but customer doesn't have a loyalty program yet.

	This ensures customers created before loyalty was enabled can still earn points.

	Args:
		doc: Sales Invoice document
	"""
	if not doc.is_pos or not doc.pos_profile or not doc.customer:
		return

	# Check if customer already has a loyalty program
	customer_loyalty = frappe.db.get_value("Customer", doc.customer, "loyalty_program")
	if customer_loyalty:
		return

	# Get POS Settings
	pos_settings = frappe.db.get_value(
		"POS Settings",
		{"pos_profile": doc.pos_profile},
		["enable_loyalty_program", "default_loyalty_program"],
		as_dict=True
	)

	if not pos_settings:
		return

	if not cint(pos_settings.get("enable_loyalty_program")):
		return

	loyalty_program = pos_settings.get("default_loyalty_program")
	if not loyalty_program:
		return

	# Assign loyalty program to customer
	frappe.db.set_value(
		"Customer",
		doc.customer,
		"loyalty_program",
		loyalty_program,
		update_modified=False
	)


def set_source_warehouse_from_pos_profile(doc):
	"""
	Set Source Warehouse from POS Profile warehouse.

	When a Sales Invoice is created via POS, automatically populate
	the set_warehouse field from the POS Profile's warehouse setting.

	Args:
		doc: Sales Invoice document
	"""
	if not doc.pos_profile:
		return

	# Only set if not already manually specified
	if doc.set_warehouse:
		return

	try:
		warehouse = frappe.db.get_value(
			"POS Profile", doc.pos_profile, "warehouse"
		)
		if warehouse:
			doc.set_warehouse = warehouse
			doc.update_stock = 1
	except Exception:
		pass


def before_cancel(doc, method=None):
	"""
	Before Cancel hook for Sales Invoice.
	Cancel any credit redemption journal entries.

	Args:
		doc: Sales Invoice document
		method: Hook method name (unused)
	"""
	try:
		from pos_itqan.api.credit_sales import cancel_credit_journal_entries
		cancel_credit_journal_entries(doc.name)
	except Exception as e:
		frappe.log_error(
			title="Credit Sale JE Cancellation Error",
			message=f"Invoice: {doc.name}, Error: {str(e)}\n{frappe.get_traceback()}"
		)
		# Don't block invoice cancellation if JE cancellation fails
		frappe.msgprint(
			_("Warning: Some credit journal entries may not have been cancelled. Please check manually."),
			alert=True,
			indicator="orange"
		)
