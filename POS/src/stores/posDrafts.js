import { deleteDraft, getDraftsCount, saveDraft, getAllDrafts, updateDraft } from "@/utils/draftManager"
import { useToast } from "@/composables/useToast"
import { call } from "@/utils/apiWrapper"
import { printKitchenOrder } from "@/utils/kitchenPrint"
import { defineStore } from "pinia"
import { ref } from "vue"

export const usePOSDraftsStore = defineStore("posDrafts", () => {
	// Use custom toast
	const { showSuccess, showError, showWarning } = useToast()

	// State
	const draftsCount = ref(0)
	const drafts = ref([])

	// Actions
	async function updateDraftsCount() {
		try {
			draftsCount.value = await getDraftsCount()
		} catch (error) {
			console.error("Error getting drafts count:", error)
		}
	}

	async function loadDrafts() {
		try {
			drafts.value = await getAllDrafts()
			draftsCount.value = drafts.value.length
		} catch (error) {
			console.error("Error loading drafts:", error)
		}
	}

	/**
	 * Get all drafts linked to a specific table
	 * @param {string} tableName - The table name (POS Table docname)
	 * @returns {Array} Drafts linked to this table
	 */
	function getDraftsForTable(tableName) {
		return drafts.value.filter(draft => {
			const draftTable = draft.table
			if (!draftTable) return false
			// Handle table as object or string
			const draftTableName = typeof draftTable === 'object' ? draftTable.name : draftTable
			return draftTableName === tableName
		})
	}

	async function saveDraftInvoice(
		invoiceItems,
		customer,
		posProfile,
		appliedOffers = [],
		draftId = null,
		table = null,
	) {
		if (invoiceItems.length === 0) {
			showWarning(__("Cannot save an empty cart as draft"))
			return null
		}

		try {
			const draftData = {
				pos_profile: posProfile,
				customer: customer,
				items: invoiceItems,
				applied_offers: appliedOffers, // Save applied offers
				table: table,
			}

			let savedDraft
			if (draftId) {
				savedDraft = await updateDraft(draftId, draftData)
			} else {
				savedDraft = await saveDraft(draftData)
			}

			// Sync table status if table is assigned - use add_order_to_table for multi-order support
			if (table) {
				const tableName = table.name || table; // Handle object or string
				const customerName = customer?.customer_name || customer?.name || customer
				try {
					await call("pos_itqan.api.tables.add_order_to_table", {
						table: tableName,
						draft_id: savedDraft.draft_id,
						customer: customerName,
					})
				} catch (e) {
					console.error("Failed to add order to table:", e)
				}
			}

			await loadDrafts() // Refresh drafts list and count

			showSuccess(__("Invoice saved as draft successfully"))

			// Auto-print kitchen order if table is assigned
			if (table) {
				const tableDisplayName = table.table_name || table.name || table
				try {
					printKitchenOrder({
						tableName: tableDisplayName,
						items: invoiceItems
					})
				} catch (e) {
					console.error('Kitchen print failed:', e)
				}
			}

			return savedDraft
		} catch (error) {
			console.error("Error saving draft:", error)
			showError(__("Failed to save draft"))
			return null
		}
	}

	async function loadDraft(draft) {
		try {
			showSuccess(__("Draft invoice loaded successfully"))

			return {
				items: draft.items || [],
				customer: draft.customer,
				applied_offers: draft.applied_offers || [], // Restore applied offers
				table: draft.table,
			}
		} catch (error) {
			console.error("Error loading draft:", error)
			showError(__("Failed to load draft"))
			throw error
		}
	}

	async function deleteDraftById(draftId, table = null) {
		try {
			await deleteDraft(draftId)

			// Remove from table's orders list if table is provided
			if (table) {
				const tableName = table.name || table
				try {
					await call("pos_itqan.api.tables.remove_order_from_table", {
						table: tableName,
						draft_id: draftId,
					})
				} catch (e) {
					console.error("Failed to remove order from table:", e)
				}
			}

			await loadDrafts() // Refresh drafts list and count
			showSuccess(__("Draft deleted successfully"))
		} catch (error) {
			console.error("Error deleting draft:", error)
			showError(__("Failed to delete draft"))
		}
	}

	/**
	 * Delete all drafts for a table (used after checkout)
	 * @param {string} tableName - The table name
	 */
	async function deleteAllDraftsForTable(tableName) {
		const tableDrafts = getDraftsForTable(tableName)
		for (const draft of tableDrafts) {
			try {
				await deleteDraft(draft.draft_id)
			} catch (e) {
				console.error("Failed to delete draft:", draft.draft_id, e)
			}
		}

		// Clear table status
		try {
			await call("pos_itqan.api.tables.update_table_status", {
				table: tableName,
				status: "Available",
				current_order: null,
				current_customer: null,
				clear_all_orders: true,
			})
		} catch (e) {
			console.error("Failed to clear table status:", e)
		}

		await loadDrafts()
	}

	return {
		// State
		draftsCount,
		drafts,

		// Actions
		updateDraftsCount,
		loadDrafts,
		saveDraftInvoice,
		loadDraft,
		deleteDraft: deleteDraftById,
		getDraftsForTable,
		deleteAllDraftsForTable,
	}
})
