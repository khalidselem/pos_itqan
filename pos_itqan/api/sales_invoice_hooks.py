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

The doc.taxes table is ALWAYS preserved when there are taxable items, because
ERPNext requires it to:
  1. Calculate tax totals
  2. Generate GL entries (VAT Payable credit)

Without tax rows, even correct item_tax_rate values produce NO accounting entries.
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
	  1. Ensure doc.taxes exists (populate from template if missing)
	  2. Set item_tax_rate = 0 for non-VAT items
	  3. Apply tax-inclusive flag from POS Settings
	  4. Let ERPNext's own validation + calculate_taxes_and_totals() finish

	CRITICAL RULES:
	  • NEVER remove doc.taxes for mixed carts — GL entries depend on it
	  • NEVER call calculate_taxes_and_totals() ourselves — ERPNext does it
	  • ONLY clear doc.taxes when ALL items are tax-exempt
	  • ALWAYS ensure doc.taxes has rows when taxable items exist
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
	Core tax override logic:
	  1. Determines which items are taxable (have Item Tax Template)
	  2. Ensures doc.taxes exists when there are taxable items
	  3. Forces item_tax_rate = {"account": 0} for non-taxable items

	This is the ONLY place where we modify tax behavior.
	"""
	log = frappe.logger("pos_tax", allow_site=True)

	item_codes = [item.item_code for item in doc.get("items") if item.item_code]
	if not item_codes:
		return

	# ── Step 1: Determine which items are taxable ──────────────────────
	items_with_tax = _get_items_with_tax_template(item_codes)

	has_any_vat_item = any(
		item.item_code in items_with_tax
		for item in doc.get("items")
		if item.item_code
	)

	# ── Step 2: Handle the all-exempt case ─────────────────────────────
	if not has_any_vat_item:
		# ALL items are tax-exempt → safe to clear the tax table entirely.
		# No tax should be calculated or posted to GL.
		doc.taxes_and_charges = None
		doc.set("taxes", [])
		log.debug("All items tax-exempt — cleared taxes table")
		return

	# ── Step 3: ENSURE tax rows exist ──────────────────────────────────
	# This is CRITICAL. ERPNext requires doc.taxes to have rows for:
	#   - Tax total calculation in calculate_taxes_and_totals()
	#   - GL entry generation (VAT Payable credit)
	# Without tax rows, item_tax_rate overrides do nothing.
	_ensure_tax_rows_exist(doc)

	# ── Step 4: Get tax account heads for zero-rate map ────────────────
	tax_accounts = _get_tax_account_heads(doc)

	if not tax_accounts:
		log.debug("No tax accounts found — skipping item_tax_rate overrides")
		return

	# ── Step 5: Force 0% tax on non-VAT items ─────────────────────────
	# Build a single zero-rate JSON string, reused for all non-VAT items.
	# CRITICAL: We KEEP doc.taxes intact so ERPNext generates GL entries.
	# We only control the per-item contribution via item_tax_rate.
	zero_rate_map = {acct: 0 for acct in tax_accounts}
	zero_rate_json = json.dumps(zero_rate_map)

	for item in doc.get("items"):
		if item.item_code and item.item_code not in items_with_tax:
			item.item_tax_rate = zero_rate_json
			log.debug(f"Forced 0% tax for non-VAT item: {item.item_code}")


def _ensure_tax_rows_exist(doc):
	"""
	Ensures doc.taxes has at least one row when there are taxable items.

	ERPNext's calculate_taxes_and_totals() requires doc.taxes to have rows.
	Without them:
	  - Tax totals will be 0
	  - No GL entry for VAT Payable is generated
	  - Tax amounts are silently absorbed into other accounts

	This function populates doc.taxes from:
	  1. The taxes_and_charges template (if set on doc)
	  2. The POS Profile's taxes_and_charges (fallback)

	It is IDEMPOTENT: if doc.taxes already has rows, it does nothing.
	"""
	# If taxes already exist, nothing to do
	if doc.get("taxes") and len(doc.get("taxes")) > 0:
		return

	log = frappe.logger("pos_tax", allow_site=True)

	# ── Try 1: Populate from the doc's taxes_and_charges template ──────
	template_name = doc.taxes_and_charges
	if not template_name and doc.pos_profile:
		# Fallback: get template from POS Profile
		template_name = frappe.db.get_value(
			"POS Profile", doc.pos_profile, "taxes_and_charges"
		)
		if template_name:
			doc.taxes_and_charges = template_name

	if not template_name:
		log.debug("No tax template found — cannot populate doc.taxes")
		return

	# ── Load template and populate tax rows ────────────────────────────
	try:
		template_doc = frappe.get_cached_doc(
			"Sales Taxes and Charges Template", template_name
		)
	except frappe.DoesNotExistError:
		log.debug(f"Tax template '{template_name}' not found")
		return

	for tax_row in template_doc.taxes:
		doc.append("taxes", {
			"charge_type": tax_row.charge_type,
			"account_head": tax_row.account_head,
			"rate": tax_row.rate,
			"description": tax_row.description,
			"included_in_print_rate": getattr(tax_row, "included_in_print_rate", 0),
		})

	log.debug(
		f"Populated {len(template_doc.taxes)} tax row(s) from template '{template_name}'"
	)


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
	Returns a list of tax account heads from doc.taxes.
	At this point, _ensure_tax_rows_exist has already been called,
	so doc.taxes should be populated.
	"""
	return [t.account_head for t in doc.get("taxes", []) if t.account_head]


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
