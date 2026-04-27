# Copyright (c) 2025, ITQAN LLC (info@itqan-kw.net, itqan-kw.com) and contributors
# For license information, please see license.txt

"""
Sales Invoice Hooks
Event handlers for Sales Invoice document events

Tax Strategy:
─────────────
All tax overrides happen in before_validate, BEFORE ERPNext's own
validate() → calculate_taxes_and_totals() runs. We NEVER call
calculate_taxes_and_totals() ourselves.

For taxable items (have Item Tax Template):
  → We clear item_tax_rate to "" (empty)
  → ERPNext's validate_item_tax_template() then sets it from the template
  → ERPNext calculates the correct tax

For non-taxable items (no Item Tax Template):
  → We set item_tax_rate = {"account": 0} (force zero)
  → We clear item_tax_template = "" (prevent ERPNext from overwriting)
  → ERPNext's validate_item_tax_template() skips them (no template)
  → ERPNext's _get_tax_rate() finds the account → returns 0
"""

import json

import frappe
from frappe import _
from frappe.utils import cint


def before_validate(doc, method=None):
	"""
	Runs BEFORE ERPNext's own validate() → calculate_taxes_and_totals().

	This is the ONLY place where we modify tax data. We:
	  1. Ensure doc.taxes has rows (required for GL entries)
	  2. Clear item_tax_rate on taxable items (let ERPNext set from template)
	  3. Force item_tax_rate = {"account": 0} on non-taxable items
	  4. Set tax-inclusive flag

	Then ERPNext's own validate() calls calculate_taxes_and_totals()
	which uses our prepared data to calculate correctly.
	"""
	if not doc.is_pos:
		return

	try:
		_apply_item_tax_overrides(doc)
	except Exception as e:
		frappe.log_error(
			f"POS tax override error: {e}\n{frappe.get_traceback()}",
			"POS VAT Override Error"
		)


def validate(doc, method=None):
	"""
	Runs AFTER ERPNext's own validate() + calculate_taxes_and_totals().
	NO tax logic here — ERPNext already calculated correctly using our
	before_validate overrides.
	"""
	auto_assign_loyalty_program_on_invoice(doc)
	set_source_warehouse_from_pos_profile(doc)


# ──────────────────────────────────────────────────────────────────────────────
# CORE TAX LOGIC
# ──────────────────────────────────────────────────────────────────────────────

def _apply_item_tax_overrides(doc):
	"""
	Prepares item-level tax data BEFORE ERPNext's calculate runs.

	Taxability is determined by dual-check:
	  1. DB: does tabItem Tax have rows for this item / its Item Group?
	  2. Row: does the invoice item row have item_tax_template set?
	If EITHER is true → item is taxable.

	Taxable items:
	  → item_tax_rate = "" (cleared)
	  → item_tax_template is KEPT
	  → ERPNext's validate_item_tax_template() will populate item_tax_rate
	    from the template, then calculate_taxes() will use that rate.

	Non-taxable items:
	  → item_tax_rate = {"account_head": 0} (forced zero)
	  → item_tax_template = "" (cleared)
	  → ERPNext's validate_item_tax_template() skips them (no template)
	  → calculate_taxes() finds account in item_tax_rate → uses 0
	"""
	log = frappe.logger("pos_tax", allow_site=True)

	item_codes = [item.item_code for item in doc.get("items") if item.item_code]
	if not item_codes:
		return

	# ── Determine which items are taxable ──────────────────────────────
	items_with_tax_in_db = _get_items_with_tax_template(item_codes)

	def _is_taxable(item):
		"""Dual-check: DB query OR invoice row field."""
		if item.item_code and item.item_code in items_with_tax_in_db:
			return True
		if item.get("item_tax_template"):
			return True
		return False

	has_any_vat_item = any(
		_is_taxable(item)
		for item in doc.get("items")
		if item.item_code
	)

	# ── All-exempt case ────────────────────────────────────────────────
	if not has_any_vat_item:
		doc.taxes_and_charges = None
		doc.set("taxes", [])
		log.debug("All items tax-exempt — cleared taxes")
		return

	# ── Ensure tax rows exist (required for GL entries) ────────────────
	_ensure_tax_rows_exist(doc)

	if not doc.get("taxes"):
		log.debug("Could not populate tax rows — skipping")
		return

	# ── Set tax-inclusive flag ──────────────────────────────────────────
	_apply_tax_inclusive_flag(doc)

	# ── Build zero-rate map ────────────────────────────────────────────
	tax_accounts = [t.account_head for t in doc.get("taxes") if t.account_head]
	if not tax_accounts:
		return

	zero_rate_map = {acct: 0 for acct in tax_accounts}
	zero_rate_json = json.dumps(zero_rate_map)

	# ── DIAGNOSTIC: Log state before overrides (visible in Error Log) ──
	diag_items = []
	for item in doc.get("items"):
		if item.item_code:
			diag_items.append({
				"item_code": item.item_code,
				"item_tax_template": item.get("item_tax_template") or "(empty)",
				"item_tax_rate_BEFORE": item.get("item_tax_rate") or "(empty)",
				"is_taxable_db": item.item_code in items_with_tax_in_db,
				"is_taxable_row": bool(item.get("item_tax_template")),
			})

	diag_taxes = []
	for t in doc.get("taxes", []):
		diag_taxes.append({
			"account_head": t.account_head,
			"rate": t.rate,
			"charge_type": t.charge_type,
		})

	frappe.log_error(
		message=json.dumps({
			"invoice": doc.name,
			"items": diag_items,
			"taxes": diag_taxes,
			"taxes_and_charges": doc.taxes_and_charges,
			"items_with_tax_in_db": list(items_with_tax_in_db),
		}, indent=2, ensure_ascii=False, default=str),
		title="POS Tax Debug: BEFORE overrides"
	)

	# ── Apply per-item overrides ───────────────────────────────────────
	# ONLY modify NON-TAXABLE items. Do NOT touch taxable items at all.
	taxable_count = 0
	exempt_count = 0

	for item in doc.get("items"):
		if not item.item_code:
			continue

		if _is_taxable(item):
			# TAXABLE: DO NOT TOUCH. Leave item_tax_rate as-is.
			# ERPNext's validate_item_tax_template() will handle it.
			taxable_count += 1
		else:
			# NON-TAXABLE: force zero rate and clear template
			item.item_tax_rate = zero_rate_json
			item.item_tax_template = ""
			exempt_count += 1

	log.debug(
		f"Tax overrides set: {taxable_count} taxable (UNTOUCHED), "
		f"{exempt_count} exempt (forced 0%). "
		f"ERPNext will now calculate_taxes_and_totals()."
	)


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_tax_rows_exist(doc):
	"""
	Ensures doc.taxes has at least one row. Required for GL entries.
	IDEMPOTENT: if doc.taxes already has rows, does nothing.
	"""
	if doc.get("taxes") and len(doc.get("taxes")) > 0:
		return

	log = frappe.logger("pos_tax", allow_site=True)

	template_name = doc.taxes_and_charges
	if not template_name and doc.pos_profile:
		template_name = frappe.db.get_value(
			"POS Profile", doc.pos_profile, "taxes_and_charges"
		)
		if template_name:
			doc.taxes_and_charges = template_name

	if not template_name:
		log.debug("No tax template found")
		return

	try:
		template_doc = frappe.get_cached_doc(
			"Sales Taxes and Charges Template", template_name
		)
	except frappe.DoesNotExistError:
		log.debug(f"Tax template '{template_name}' not found")
		return

	if not template_doc.taxes:
		return

	for tax_row in template_doc.taxes:
		doc.append("taxes", {
			"charge_type": tax_row.charge_type,
			"account_head": tax_row.account_head,
			"rate": tax_row.rate,
			"description": tax_row.description or tax_row.account_head,
			"included_in_print_rate": getattr(tax_row, "included_in_print_rate", 0),
		})

	log.debug(f"Injected {len(template_doc.taxes)} tax row(s) from '{template_name}'")


def _get_items_with_tax_template(item_codes):
	"""
	Returns a set of item_codes that have an Item Tax Template assigned,
	either directly on the Item or inherited from their Item Group.
	"""
	items_with_tax = set()

	# 1. Item-level
	tax_results = frappe.db.sql(
		"SELECT DISTINCT parent FROM `tabItem Tax` WHERE parent IN %s AND parenttype = 'Item'",
		(tuple(item_codes),),
	)
	items_with_tax.update(row[0] for row in tax_results)

	# 2. Item Group-level
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
	"""Set included_in_print_rate flag based on POS Settings."""
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
	"""Auto-assign loyalty program to customer if enabled in POS Settings."""
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
		"Customer", doc.customer, "loyalty_program",
		loyalty_program, update_modified=False
	)


def set_source_warehouse_from_pos_profile(doc):
	"""Set Source Warehouse from POS Profile warehouse."""
	if not doc.pos_profile or doc.set_warehouse:
		return

	try:
		warehouse = frappe.db.get_value("POS Profile", doc.pos_profile, "warehouse")
		if warehouse:
			doc.set_warehouse = warehouse
			doc.update_stock = 1
	except Exception:
		pass


def before_cancel(doc, method=None):
	"""Cancel credit redemption journal entries."""
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
