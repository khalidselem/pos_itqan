# Copyright (c) 2025, ITQAN LLC (info@itqan-kw.net, itqan-kw.com) and contributors
# For license information, please see license.txt

"""
Sales Invoice Hooks
Event handlers for Sales Invoice document events

Tax Strategy:
─────────────
Tax data (item_tax_template, item_tax_rate, doc.taxes) is populated
directly in update_invoice() via _populate_item_tax_data() — BEFORE
set_missing_values() and calculate_taxes_and_totals().

This hook only handles:
  - Tax-inclusive flag from POS Settings
  - Loyalty program auto-assignment
  - Warehouse assignment
"""

import frappe
from frappe import _
from frappe.utils import cint


def before_validate(doc, method=None):
	"""Apply tax-inclusive flag if needed."""
	if not doc.is_pos:
		return

	_apply_tax_inclusive_flag(doc)


def validate(doc, method=None):
	"""Post-validation: loyalty program and warehouse."""
	auto_assign_loyalty_program_on_invoice(doc)
	set_source_warehouse_from_pos_profile(doc)


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
