# Copyright (c) 2025, ITQAN LLC (info@itqan-kw.net, itqan-kw.com) and contributors
# For license information, please see license.txt

"""
Sales Invoice Hooks
Event handlers for Sales Invoice document events

Tax Strategy:
─────────────
We NEVER disable ERPNext's tax engine. Instead, we control tax at the ITEM level
using `item_tax_rate` overrides:

  • Items WITH an Item Tax Template → left untouched (ERPNext applies normal tax)
  • Items WITHOUT an Item Tax Template → item_tax_rate forced to {"account": 0}

This approach:
  ✅ Preserves the doc.taxes table (required for GL entries)
  ✅ Lets ERPNext's calculate_taxes_and_totals() run normally
  ✅ Generates correct GL entries (VAT Payable is credited)
  ✅ Handles mixed carts (taxable + exempt items)
  ✅ Is idempotent (safe to run multiple times)
"""

import json

import frappe
from frappe import _
from frappe.utils import cint


def validate(doc, method=None):
	"""
	Validate hook for Sales Invoice.
	Auto-assign loyalty program to customer if enabled.
	Set source warehouse from POS Profile.

	Args:
		doc: Sales Invoice document
		method: Hook method name (unused)
	"""
	auto_assign_loyalty_program_on_invoice(doc)
	set_source_warehouse_from_pos_profile(doc)


def before_validate(doc, method=None):
	"""
	Runs BEFORE standard Frappe validation.

	Execution order:
	  1. Set item_tax_rate = 0 for non-VAT items (MUST happen before tax calc)
	  2. Apply tax-inclusive setting from POS Settings
	  3. Let ERPNext's own validation + calculate_taxes_and_totals() finish

	CRITICAL RULES:
	  • NEVER remove doc.taxes for mixed carts — GL entries depend on it
	  • NEVER call calculate_taxes_and_totals() ourselves — ERPNext does it
	  • ONLY clear doc.taxes when ALL items are tax-exempt
	"""
	if not doc.is_pos:
		return

	try:
		_apply_item_level_tax_overrides(doc)
	except Exception as e:
		frappe.log_error(
			f"Error in item-level tax override: {e}\n{frappe.get_traceback()}",
			"POS VAT Override Error"
		)

	# Apply tax-inclusive setting AFTER item_tax_rate overrides are locked in.
	# This only sets the included_in_print_rate flag — it does NOT call
	# calculate_taxes_and_totals() since ERPNext will do that during validation.
	_apply_tax_inclusive_flag(doc)


def _apply_item_level_tax_overrides(doc):
	"""
	Core tax override logic. Sets item_tax_rate = {"account": 0} for items
	that do NOT have an Item Tax Template (directly or via Item Group).

	This is the ONLY place where we modify tax behavior. We never touch
	doc.taxes except in the all-exempt case.
	"""
	log = frappe.logger("pos_tax", allow_site=True)

	item_codes = [item.item_code for item in doc.get("items") if item.item_code]
	if not item_codes:
		return

	# ── Step 1: Determine which items are taxable ──────────────────────
	items_with_tax = _get_items_with_tax_template(item_codes)

	# ── Step 2: Determine tax account heads ────────────────────────────
	# We need the account heads to build the zero-rate override map.
	# Check both the template name AND the existing tax rows.
	tax_accounts = _get_tax_account_heads(doc)

	# ── Step 3: Handle the all-exempt case ─────────────────────────────
	has_any_vat_item = any(
		item.item_code in items_with_tax
		for item in doc.get("items")
		if item.item_code
	)

	if not has_any_vat_item:
		# ALL items are tax-exempt → safe to clear the tax table entirely.
		# This prevents any residual tax from being calculated or posted.
		doc.taxes_and_charges = None
		doc.set("taxes", [])
		log.debug("All items tax-exempt — cleared taxes table")
		return

	# ── Step 4: Mixed cart — force 0% on non-VAT items ─────────────────
	# CRITICAL: We KEEP doc.taxes intact so ERPNext can generate GL entries.
	# We only control the per-item contribution via item_tax_rate.
	if not tax_accounts:
		# No tax accounts found — nothing to override
		return

	# Build a single zero-rate JSON string, reused for all non-VAT items.
	zero_rate_map = {acct: 0 for acct in tax_accounts}
	zero_rate_json = json.dumps(zero_rate_map)

	for item in doc.get("items"):
		if item.item_code and item.item_code not in items_with_tax:
			item.item_tax_rate = zero_rate_json
			log.debug(f"Forced 0% tax for non-VAT item: {item.item_code}")


def _get_items_with_tax_template(item_codes):
	"""
	Returns a set of item_codes that have an Item Tax Template assigned,
	either directly on the Item or inherited from their Item Group.
	"""
	items_with_tax = set()

	# 1. Check Item-level tax templates (tabItem Tax with parenttype = 'Item')
	tax_results = frappe.db.sql(
		"SELECT DISTINCT parent FROM `tabItem Tax` WHERE parent IN %s AND parenttype = 'Item'",
		(tuple(item_codes),),
	)
	items_with_tax.update(row[0] for row in tax_results)

	# 2. Check Item Group-level tax templates
	item_details = frappe.get_all(
		"Item",
		filters={"name": ["in", item_codes]},
		fields=["name", "item_group"]
	)

	item_to_group = {}
	for row in item_details:
		if row.get("item_group"):
			item_to_group[row["name"]] = row["item_group"]

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

	return items_with_tax


def _get_tax_account_heads(doc):
	"""
	Returns a list of tax account heads that apply to this invoice.
	Checks both the taxes_and_charges template AND the doc.taxes rows.
	"""
	tax_accounts = []

	# First try: get from the named template (most reliable)
	if doc.taxes_and_charges:
		template_taxes = frappe.db.get_all(
			"Sales Taxes and Charges",
			filters={"parent": doc.taxes_and_charges},
			fields=["account_head"]
		)
		tax_accounts = [t.account_head for t in template_taxes if t.account_head]

	# Fallback: get from existing tax rows on the document
	if not tax_accounts:
		tax_accounts = [t.account_head for t in doc.get("taxes", []) if t.account_head]

	return tax_accounts


def _apply_tax_inclusive_flag(doc):
	"""
	Set the included_in_print_rate flag on tax rows based on POS Settings.

	This ONLY sets the flag. It does NOT call calculate_taxes_and_totals()
	because ERPNext will do that automatically during its own validation cycle.
	Calling it prematurely would cause tax to be calculated before our
	item_tax_rate overrides take effect.

	Args:
		doc: Sales Invoice document
	"""
	if not doc.pos_profile:
		return

	# No tax rows → nothing to flag
	if not doc.get("taxes"):
		return

	try:
		pos_settings = frappe.db.get_value(
			"POS Settings",
			{"pos_profile": doc.pos_profile},
			["tax_inclusive"],
			as_dict=True
		)
		tax_inclusive = pos_settings.get("tax_inclusive", 0) if pos_settings else 0
	except Exception:
		tax_inclusive = 0

	for tax in doc.get("taxes", []):
		# Actual charge type cannot be inclusive
		if tax.charge_type == "Actual":
			tax.included_in_print_rate = 0
			continue

		tax.included_in_print_rate = 1 if tax_inclusive else 0


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
