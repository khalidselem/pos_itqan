# Copyright (c) 2025, ITQAN LLC (info@itqan-kw.net, itqan-kw.com) and contributors
# For license information, please see license.txt

"""
Sales Invoice Hooks
Event handlers for Sales Invoice document events

Tax Strategy (Final):
─────────────────────
ERPNext applies taxes globally when doc.taxes exists. To achieve per-item
tax control, we use item_tax_rate overrides AND we must apply them AFTER
ERPNext's own validate() + calculate_taxes_and_totals() runs.

Why? Because ERPNext's calculate_taxes_and_totals() calls
validate_item_tax_template() which OVERWRITES item_tax_rate from the
item_tax_template field. Our overrides set in before_validate get wiped.

Solution: The validate hook (runs AFTER ERPNext's validate) has the FINAL
WORD. It re-applies item_tax_rate overrides and calls
calculate_taxes_and_totals() one more time with the correct data.

Flow:
  1. before_validate (ours) → ensure tax rows exist, handle all-exempt case
  2. validate (ERPNext's)   → calculate_taxes_and_totals() (may overwrite)
  3. validate (ours)        → FINAL: re-apply overrides + recalculate
"""

import json

import frappe
from frappe import _
from frappe.utils import cint


# ──────────────────────────────────────────────────────────────────────────────
# HOOK: before_validate
# ──────────────────────────────────────────────────────────────────────────────
# Runs BEFORE ERPNext's own validate().
# Handles setup work:
#   - All-exempt case: clear taxes early (optimization)
#   - Ensure tax rows exist for ERPNext's calculate to work
#   - Set tax-inclusive flag
# ──────────────────────────────────────────────────────────────────────────────

def before_validate(doc, method=None):
	"""
	Setup phase. Ensures doc.taxes exists and flags are set.
	The actual item_tax_rate enforcement happens in the validate hook.
	"""
	if not doc.is_pos:
		return

	try:
		item_codes = [item.item_code for item in doc.get("items") if item.item_code]
		if not item_codes:
			return

		items_with_tax = _get_items_with_tax_template(item_codes)
		has_any_vat_item = any(
			(item.item_code in items_with_tax) or item.get("item_tax_template")
			for item in doc.get("items")
			if item.item_code
		)

		if not has_any_vat_item:
			# ALL items are tax-exempt → clear taxes entirely
			doc.taxes_and_charges = None
			doc.set("taxes", [])
			return

		# Ensure tax rows exist for ERPNext's calculate_taxes_and_totals()
		_ensure_tax_rows_exist(doc)

		# Set tax-inclusive flag before ERPNext calculates
		_apply_tax_inclusive_flag(doc)

	except Exception as e:
		frappe.log_error(
			f"Error in before_validate tax setup: {e}\n{frappe.get_traceback()}",
			"POS VAT Override Error"
		)


# ──────────────────────────────────────────────────────────────────────────────
# HOOK: validate
# ──────────────────────────────────────────────────────────────────────────────
# Runs AFTER ERPNext's own validate() and calculate_taxes_and_totals().
# This is the FINAL WORD on tax calculation.
#
# ERPNext's calculate_taxes_and_totals() calls validate_item_tax_template()
# which overwrites item_tax_rate. So we must re-apply our overrides HERE
# and recalculate.
# ──────────────────────────────────────────────────────────────────────────────

def validate(doc, method=None):
	"""
	FINAL tax enforcement. Runs AFTER ERPNext's own validate.
	Re-applies item_tax_rate overrides and recalculates.
	"""
	if doc.is_pos:
		_enforce_item_level_tax(doc)

	auto_assign_loyalty_program_on_invoice(doc)
	set_source_warehouse_from_pos_profile(doc)


def _enforce_item_level_tax(doc):
	"""
	The AUTHORITATIVE, FINAL tax enforcement.
	Runs AFTER ERPNext's own validate() + calculate_taxes_and_totals().

	Determines taxability using TWO checks (dual-check):
	  1. DB query: does the Item master / Item Group have rows in tabItem Tax?
	  2. Invoice row: does item.item_tax_template have a value?
	If EITHER is true, the item is taxable and we DO NOT touch it.
	Only items that fail BOTH checks get forced to 0%.
	"""
	log = frappe.logger("pos_tax", allow_site=True)

	item_codes = [item.item_code for item in doc.get("items") if item.item_code]
	if not item_codes:
		return

	# DB-level check: which items have tax templates in their master data
	items_with_tax_in_db = _get_items_with_tax_template(item_codes)

	# Dual-check: an item is taxable if EITHER:
	#   - DB query found a tax template for it, OR
	#   - The invoice row has item_tax_template set (by ERPNext's set_missing_values)
	def _is_item_taxable(item):
		if item.item_code in items_with_tax_in_db:
			return True
		if item.get("item_tax_template"):
			return True
		return False

	has_any_vat_item = any(
		_is_item_taxable(item)
		for item in doc.get("items")
		if item.item_code
	)

	# ── All-exempt: clear taxes ────────────────────────────────────────
	if not has_any_vat_item:
		doc.taxes_and_charges = None
		doc.set("taxes", [])
		doc.total_taxes_and_charges = 0
		doc.calculate_taxes_and_totals()
		log.debug("All items tax-exempt — cleared taxes and recalculated")
		return

	# ── Ensure tax rows exist ──────────────────────────────────────────
	_ensure_tax_rows_exist(doc)

	if not doc.get("taxes") or len(doc.get("taxes")) == 0:
		log.debug("Could not populate tax rows — skipping enforcement")
		return

	# ── Apply tax-inclusive flag ────────────────────────────────────────
	_apply_tax_inclusive_flag(doc)

	# ── Build zero-rate map from actual tax rows ───────────────────────
	tax_accounts = [t.account_head for t in doc.get("taxes") if t.account_head]
	if not tax_accounts:
		return

	zero_rate_map = {acct: 0 for acct in tax_accounts}
	zero_rate_json = json.dumps(zero_rate_map)

	# ── Force overrides ONLY on non-taxable items ─────────────────────
	# CRITICAL: We check BOTH the DB query AND item.item_tax_template.
	# If EITHER indicates the item is taxable, we DO NOT touch it.
	overridden_count = 0
	preserved_count = 0
	for item in doc.get("items"):
		if not item.item_code:
			continue

		if _is_item_taxable(item):
			# TAXABLE — do NOT modify, let ERPNext handle normally
			preserved_count += 1
			continue

		# NON-TAXABLE — force zero tax
		item.item_tax_rate = zero_rate_json
		item.item_tax_template = ""  # Prevent ERPNext from overwriting
		overridden_count += 1

	# ── Recalculate with correct overrides ─────────────────────────────
	doc.calculate_taxes_and_totals()

	log.debug(
		f"Tax enforcement: {preserved_count} taxable (untouched), "
		f"{overridden_count} non-taxable (forced 0%), "
		f"total_taxes = {doc.total_taxes_and_charges}"
	)


# ──────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_tax_rows_exist(doc):
	"""
	Ensures doc.taxes has at least one row when there are taxable items.
	IDEMPOTENT: if doc.taxes already has rows, does nothing.
	"""
	if doc.get("taxes") and len(doc.get("taxes")) > 0:
		return

	log = frappe.logger("pos_tax", allow_site=True)

	# Resolve template name
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

	# Load template and create tax rows
	try:
		template_doc = frappe.get_cached_doc(
			"Sales Taxes and Charges Template", template_name
		)
	except frappe.DoesNotExistError:
		log.debug(f"Tax template '{template_name}' not found")
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
		f"Injected {len(template_doc.taxes)} tax row(s) from '{template_name}'"
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
