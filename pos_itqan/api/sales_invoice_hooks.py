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


# ──────────────────────────────────────────────────────────────────────────────
# HOOK: before_validate
# ──────────────────────────────────────────────────────────────────────────────
# Runs BEFORE ERPNext's own validate() method.
# This is where we:
#   1. Ensure doc.taxes has rows (populate from template if missing)
#   2. Set item_tax_rate = 0 for non-VAT items
#   3. Apply tax-inclusive flag
# ERPNext's validate() then calls calculate_taxes_and_totals() with our data.
# ──────────────────────────────────────────────────────────────────────────────

def before_validate(doc, method=None):
	"""
	Runs BEFORE standard Frappe/ERPNext validation.
	Sets up tax rows and item-level overrides so that when ERPNext's
	calculate_taxes_and_totals() runs during validate(), it has correct data.
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

	_apply_tax_inclusive_flag(doc)


# ──────────────────────────────────────────────────────────────────────────────
# HOOK: validate
# ──────────────────────────────────────────────────────────────────────────────
# Runs AFTER ERPNext's own validate() and calculate_taxes_and_totals().
# This is our safety net: if taxes were somehow cleared during validation,
# we re-inject them and recalculate.
# ──────────────────────────────────────────────────────────────────────────────

def validate(doc, method=None):
	"""
	Validate hook for Sales Invoice.
	Runs AFTER ERPNext's own validate() + calculate_taxes_and_totals().

	Safety net: if doc.taxes got cleared during the validate cycle,
	re-inject them and force a recalculation.
	"""
	if doc.is_pos:
		_safety_net_ensure_taxes(doc)

	auto_assign_loyalty_program_on_invoice(doc)
	set_source_warehouse_from_pos_profile(doc)


def _safety_net_ensure_taxes(doc):
	"""
	Post-validation safety net.
	If doc.taxes is empty but there ARE taxable items, re-inject tax rows
	and force recalculation. This catches edge cases where ERPNext's own
	validate() cleared our tax rows.
	"""
	item_codes = [item.item_code for item in doc.get("items") if item.item_code]
	if not item_codes:
		return

	items_with_tax = _get_items_with_tax_template(item_codes)
	has_any_vat_item = any(
		item.item_code in items_with_tax
		for item in doc.get("items")
		if item.item_code
	)

	if not has_any_vat_item:
		return  # All exempt — no taxes needed

	# If taxes exist, everything is fine
	if doc.get("taxes") and len(doc.get("taxes")) > 0:
		return

	# TAXES ARE MISSING but we have taxable items → re-inject
	log = frappe.logger("pos_tax", allow_site=True)
	log.debug("Safety net: doc.taxes empty after validate — re-injecting")

	_ensure_tax_rows_exist(doc)
	_apply_tax_inclusive_flag(doc)

	if doc.get("taxes") and len(doc.get("taxes")) > 0:
		# Force item_tax_rate overrides again
		tax_accounts = [t.account_head for t in doc.get("taxes") if t.account_head]
		if tax_accounts:
			zero_rate_map = {acct: 0 for acct in tax_accounts}
			zero_rate_json = json.dumps(zero_rate_map)
			for item in doc.get("items"):
				if item.item_code and item.item_code not in items_with_tax:
					item.item_tax_rate = zero_rate_json

		# Recalculate with the correct data
		doc.calculate_taxes_and_totals()
		log.debug(f"Safety net: recalculated — total_taxes_and_charges = {doc.total_taxes_and_charges}")


# ──────────────────────────────────────────────────────────────────────────────
# CORE LOGIC
# ──────────────────────────────────────────────────────────────────────────────

def _apply_item_level_tax_overrides(doc):
	"""
	Core tax override logic:
	  1. Determines which items are taxable (have Item Tax Template)
	  2. If ALL exempt → clear doc.taxes entirely
	  3. If ANY taxable → ensure doc.taxes has rows, then force 0% on non-VAT items
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
		doc.taxes_and_charges = None
		doc.set("taxes", [])
		log.debug("All items tax-exempt — cleared taxes table")
		return

	# ── Step 3: ENSURE tax rows exist ──────────────────────────────────
	_ensure_tax_rows_exist(doc)

	# ── Step 4: Get tax accounts and force 0% on non-VAT items ────────
	tax_accounts = [t.account_head for t in doc.get("taxes", []) if t.account_head]

	if not tax_accounts:
		log.debug("No tax accounts found after ensure — skipping overrides")
		return

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

	Populates from:
	  1. The taxes_and_charges template already on the doc
	  2. The POS Profile's taxes_and_charges (fallback)

	IDEMPOTENT: if doc.taxes already has rows, does nothing.
	"""
	if doc.get("taxes") and len(doc.get("taxes")) > 0:
		return

	log = frappe.logger("pos_tax", allow_site=True)

	# ── Resolve template name ──────────────────────────────────────────
	template_name = doc.taxes_and_charges

	if not template_name and doc.pos_profile:
		template_name = frappe.db.get_value(
			"POS Profile", doc.pos_profile, "taxes_and_charges"
		)
		if template_name:
			doc.taxes_and_charges = template_name
			log.debug(f"Set taxes_and_charges from POS Profile: {template_name}")

	if not template_name:
		log.debug("No tax template found — cannot populate doc.taxes")
		return

	# ── Load template and create tax rows ──────────────────────────────
	try:
		template_doc = frappe.get_cached_doc(
			"Sales Taxes and Charges Template", template_name
		)
	except frappe.DoesNotExistError:
		log.debug(f"Tax template '{template_name}' not found in DB")
		return

	if not template_doc.taxes:
		log.debug(f"Tax template '{template_name}' has no tax rows")
		return

	for tax_row in template_doc.taxes:
		doc.append("taxes", {
			"charge_type": tax_row.charge_type,
			"account_head": tax_row.account_head,
			"rate": tax_row.rate,
			"description": tax_row.description or tax_row.account_head,
			"included_in_print_rate": getattr(tax_row, "included_in_print_rate", 0),
		})

	log.debug(
		f"Injected {len(template_doc.taxes)} tax row(s) from template '{template_name}'"
	)


def _get_items_with_tax_template(item_codes):
	"""
	Returns a set of item_codes that have an Item Tax Template assigned,
	either directly on the Item or inherited from their Item Group.
	"""
	items_with_tax = set()

	# 1. Check Item-level tax templates
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


def _apply_tax_inclusive_flag(doc):
	"""
	Set the included_in_print_rate flag on tax rows based on POS Settings.
	Does NOT call calculate_taxes_and_totals() — ERPNext does that.
	"""
	if not doc.pos_profile or not doc.get("taxes"):
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
		if tax.charge_type == "Actual":
			tax.included_in_print_rate = 0
			continue
		tax.included_in_print_rate = 1 if tax_inclusive else 0


# ──────────────────────────────────────────────────────────────────────────────
# OTHER HOOKS
# ──────────────────────────────────────────────────────────────────────────────

def auto_assign_loyalty_program_on_invoice(doc):
	"""
	Auto-assign loyalty program to customer if loyalty is enabled in POS Settings
	but customer doesn't have a loyalty program yet.
	"""
	if not doc.is_pos or not doc.pos_profile or not doc.customer:
		return

	customer_loyalty = frappe.db.get_value("Customer", doc.customer, "loyalty_program")
	if customer_loyalty:
		return

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
	"""
	if not doc.pos_profile:
		return

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
	"""
	try:
		from pos_itqan.api.credit_sales import cancel_credit_journal_entries
		cancel_credit_journal_entries(doc.name)
	except Exception as e:
		frappe.log_error(
			title="Credit Sale JE Cancellation Error",
			message=f"Invoice: {doc.name}, Error: {str(e)}\n{frappe.get_traceback()}"
		)
		frappe.msgprint(
			_("Warning: Some credit journal entries may not have been cancelled. Please check manually."),
			alert=True,
			indicator="orange"
		)
