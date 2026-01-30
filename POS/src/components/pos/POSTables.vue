<template>
  <div class="fixed inset-0 z-[500] flex bg-black/50 backdrop-blur-sm" @click.self="emit('close')">
    <div class="ms-auto w-full max-w-4xl bg-white shadow-2xl flex flex-col h-full animate-slide-left">
      <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-amber-50 to-orange-50">
          <div class="flex items-center gap-3">
            <div class="p-2 bg-amber-100 rounded-lg">
              <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
            </div>
            <div>
              <h2 class="text-xl font-bold text-gray-900">{{ __('Restaurant Tables') }}</h2>
              <p class="text-sm text-gray-600">{{ __('Manage dining tables and active orders') }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button 
              @click="fetchData" 
              class="p-2 hover:bg-white/50 rounded-lg transition-colors flex items-center justify-center"
              :title="__('Refresh')"
            >
              <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button @click="emit('close')" class="p-2 hover:bg-white/50 rounded-lg transition-colors">
              <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

      <!-- Filters & Stats -->
      <div class="px-6 py-4 border-b bg-gray-50 flex flex-wrap gap-4 items-center justify-between">
        <div class="flex gap-2">
            <button 
                v-for="zone in zones" 
                :key="zone.name"
                @click="selectedZone = zone.name"
                class="px-4 py-1.5 rounded-full text-sm font-medium transition-all border"
                :class="selectedZone === zone.name ? 'bg-amber-600 text-white border-amber-600 shadow-md' : 'bg-white text-gray-600 border-gray-200 hover:border-amber-300'"
            >
                {{ zone.zone_name }}
            </button>
            <button 
                @click="selectedZone = 'All'"
                class="px-4 py-1.5 rounded-full text-sm font-medium transition-all border"
                :class="selectedZone === 'All' ? 'bg-amber-600 text-white border-amber-600 shadow-md' : 'bg-white text-gray-600 border-gray-200 hover:border-amber-300'"
            >
                {{ __('All Zones') }}
            </button>
        </div>

        <div class="flex gap-4 text-xs">
            <div class="flex items-center gap-1.5">
                <span class="w-3 h-3 rounded-full bg-emerald-500"></span>
                <span class="text-gray-600">{{ __('Available') }} ({{ statusCounts.Available }})</span>
            </div>
            <div class="flex items-center gap-1.5">
                <span class="w-3 h-3 rounded-full bg-orange-500"></span>
                <span class="text-gray-600">{{ __('Reserved') }} ({{ statusCounts.Reserved }})</span>
            </div>
            <div class="flex items-center gap-1.5">
                <span class="w-3 h-3 rounded-full bg-red-500"></span>
                <span class="text-gray-600">{{ __('Occupied') }} ({{ statusCounts.Occupied }})</span>
            </div>
        </div>
      </div>

      <!-- Tables Grid -->
      <div class="flex-1 overflow-y-auto p-6">
        <div v-if="loading" class="flex items-center justify-center h-full">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500"></div>
        </div>

        <div v-else-if="filteredTables.length === 0" class="flex flex-col items-center justify-center h-full text-gray-400">
            <svg class="w-20 h-20 mb-4 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <p class="text-lg">{{ __('No tables found in this zone') }}</p>
        </div>

        <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            <div 
                v-for="table in filteredTables" 
                :key="table.name"
                @click="onTableClick(table)"
                class="relative group cursor-pointer transition-all duration-300"
            >
                <!-- Table Card -->
                <div 
                    class="h-32 rounded-2xl border-2 p-3 flex flex-col justify-between transition-all"
                    :class="[
                        getStatusClasses(table.status),
                        'hover:shadow-lg hover:-translate-y-1'
                    ]"
                >
                    <div class="flex justify-between items-start">
                        <span class="text-lg font-bold">{{ table.table_name }}</span>
                        <div class="flex items-center gap-1 text-[10px] opacity-70">
                            <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
                            </svg>
                            {{ table.capacity }}
                        </div>
                    </div>

                    <div v-if="table.status === 'Occupied'" class="mt-auto">
                        <!-- Customer Name - prominently displayed -->
                        <div class="text-sm font-bold truncate">
                            {{ getTableCustomerName(table) }}
                        </div>
                        <!-- Order count badge -->
                        <div class="flex items-center gap-2 mt-1">
                            <span v-if="getTableOrderCount(table) > 1" class="px-1.5 py-0.5 bg-blue-500 text-white text-[9px] font-bold rounded-full">
                                {{ getTableOrderCount(table) }} {{ __('orders') }}
                            </span>
                            <span v-else class="text-[10px] truncate opacity-60">{{ table.current_order }}</span>
                        </div>
                    </div>

                    <div class="mt-auto flex justify-between items-center">
                        <span class="px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider bg-white/30">
                            {{ table.status }}
                        </span>
                    </div>
                </div>

                <!-- Quick Action Overlay & Button -->
                <div v-if="table.status === 'Occupied'" class="absolute top-2 right-2 z-10">
                    <button 
                        @click="viewOrder(table, $event)"
                        class="p-1.5 bg-white/90 hover:bg-white text-gray-600 hover:text-blue-600 rounded-full shadow-sm transition-colors border border-gray-100"
                        :title="__('View Order Details')"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0zm-3 8c-7 0-9-5-9-5s2-5 9-5 9 5 9 5-2 5-9 5z" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
      </div>
    </div>

    <!-- Order Details Modal -->
    <div v-if="showDetailsModal && selectedTableOrder" class="fixed inset-0 z-[600] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" @click.self="closeDetailsModal">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-scale-up border border-gray-100">
            <div class="px-6 py-4 border-b bg-gray-50 flex items-center justify-between">
                <div>
                    <h3 class="text-lg font-bold text-gray-900">{{ selectedTableOrder.tableName }}</h3>
                    <p class="text-sm text-gray-500">{{ selectedTableOrder.customer || __('No Customer') }}</p>
                </div>
                <button @click="closeDetailsModal" class="p-1 hover:bg-gray-200 rounded-full transition-colors">
                    <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
            </div>
            
            <div class="p-6 max-h-[60vh] overflow-y-auto custom-scrollbar">
                <div v-if="selectedTableOrder.items.length === 0" class="text-center text-gray-400 py-8 flex flex-col items-center">
                    <div class="p-3 bg-gray-50 rounded-full mb-3">
                        <svg class="w-6 h-6 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" /></svg>
                    </div>
                    {{ __('No items in this order') }}
                </div>
                <ul v-else class="space-y-3">
                    <li v-for="(item, idx) in selectedTableOrder.items" :key="idx" class="flex justify-between items-start text-sm group">
                        <div class="flex gap-3">
                            <span class="font-bold text-gray-500 w-6 pt-0.5">{{ item.qty || item.quantity }}x</span>
                            <div class="flex flex-col">
                                <p class="font-medium text-gray-900 group-hover:text-blue-600 transition-colors">{{ item.item_name || item.item_code }}</p>
                                <p v-if="item.description && item.description !== item.item_name" class="text-[10px] text-gray-400 truncate max-w-[180px]">{{ item.description }}</p>
                            </div>
                        </div>
                        <span class="font-semibold text-gray-900">{{ formatCurrency(item.amount || ((item.qty || item.quantity) * (item.rate || item.price_list_rate))) }}</span>
                    </li>
                </ul>
            </div>

            <div class="px-6 py-4 border-t bg-gray-50 flex flex-col gap-3">
                <div class="flex justify-between items-center text-lg font-bold text-gray-900">
                    <span>{{ __('Total') }}</span>
                    <span class="text-emerald-600">{{ formatCurrency(selectedTableOrder.total) }}</span>
                </div>
                <div class="grid grid-cols-3 gap-3">
                    <button @click="closeDetailsModal" class="px-3 py-2.5 bg-white border border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-colors">
                        {{ __('Close') }}
                    </button>
                    <button @click="submitOrderFromDetails" class="px-3 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors shadow-sm hover:shadow-md flex items-center justify-center gap-2">
                        <span>{{ __('Open Order') }}</span>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0zm-3 8c-7 0-9-5-9-5s2-5 9-5 9 5 9 5-2 5-9 5z" /></svg>
                    </button>
                    <button @click="checkoutFromDetails" class="px-3 py-2.5 bg-green-600 text-white font-semibold rounded-xl hover:bg-green-700 transition-colors shadow-sm hover:shadow-md flex items-center justify-center gap-2">
                        <span>{{ __('Checkout') }}</span>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
                    </button>
                </div>
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { call } from '@/utils/apiWrapper'
import { useFormatters } from '@/composables/useFormatters'
import { usePOSDraftsStore } from '@/stores/posDrafts'

const emit = defineEmits(['close', 'table-selected', 'checkout-table'])
const { formatCurrency } = useFormatters()
const draftsStore = usePOSDraftsStore()

const tables = ref([])
const zones = ref([])
const loading = ref(true)
const selectedZone = ref('All')

// Order details state
const showDetailsModal = ref(false)
const selectedTableOrder = ref(null)

const fetchData = async () => {
    loading.value = true
    try {
        const [tablesRes, zonesRes] = await Promise.all([
            call('pos_itqan.api.tables.get_tables'),
            call('pos_itqan.api.tables.get_zones')
        ])
        tables.value = tablesRes || []
        zones.value = zonesRes || []
        // Ensure drafts are loaded to cross-reference orders
        await draftsStore.loadDrafts()
    } catch (e) {
        console.error("Fetch Tables Error:", e)
    } finally {
        loading.value = false
    }
}

const filteredTables = computed(() => {
    if (selectedZone.value === 'All') return tables.value
    return tables.value.filter(t => t.zone === selectedZone.value)
})

const statusCounts = computed(() => {
    const counts = { Available: 0, Occupied: 0, Reserved: 0 }
    filteredTables.value.forEach(t => {
        if (counts[t.status] !== undefined) {
            counts[t.status]++
        }
    })
    return counts
})

const getStatusClasses = (status) => {
    switch (status) {
        case 'Available': return 'bg-white border-emerald-100 text-emerald-700'
        case 'Occupied': return 'bg-white border-red-200 shadow-sm'
        case 'Reserved': return 'bg-orange-50 border-orange-200 text-orange-700'
        case 'Disabled': return 'bg-gray-100 border-gray-200 text-gray-400 grayscale'
        default: return 'bg-white border-gray-100 text-gray-500'
    }
}

/**
 * Get the customer name for a table (from table or linked drafts)
 */
const getTableCustomerName = (table) => {
    // First check table's current_customer field
    if (table.current_customer) {
        return table.current_customer
    }
    
    // Then check linked drafts
    if (table.current_order) {
        const draft = draftsStore.drafts.find(d => 
            d.name === table.current_order || 
            d.draft_id === table.current_order || 
            d.invoice_name === table.current_order
        )
        if (draft?.customer) {
            const customer = draft.customer
            if (typeof customer === 'object' && customer !== null) {
                return customer.customer_name || customer.name || __('No Customer')
            }
            return customer
        }
    }
    
    return __('No Customer')
}

/**
 * Get the number of orders linked to a table
 */
const getTableOrderCount = (table) => {
    // Check orders array (new multi-order format)
    if (Array.isArray(table.orders)) {
        return table.orders.length
    }
    // Fallback to checking if current_order exists
    return table.current_order ? 1 : 0
}

const onTableClick = (table) => {
    if (table.status === 'Disabled') return
    emit('table-selected', table)
}

const viewOrder = (table, event) => {
    event.stopPropagation() // Prevent selecting table immediately
    
    // Find the draft for this table
    const draftId = table.current_order
    const draft = draftsStore.drafts.find(d => d.name === draftId || d.draft_id === draftId || d.invoice_name === draftId)
    
    if (draft) {
        // Calculate total
        const total = (draft.items || []).reduce((sum, item) => {
            const qty = item.qty || item.quantity || 0
            const rate = item.rate || item.price_list_rate || 0
            return sum + (qty * rate)
        }, 0)

        selectedTableOrder.value = {
            tableName: table.table_name,
            items: draft.items || [],
            customer: draft.customer_name || draft.customer || table.current_customer,
            total,
            status: 'Unpaid'
        }
        showDetailsModal.value = true
    } else {
        // Fallback if draft not found locally (maybe needs fetch)
        console.warn("Draft not found locally for table:", table.table_name)
        // Could implement single fetch here if needed
    }
}

const closeDetailsModal = () => {
    showDetailsModal.value = false
    selectedTableOrder.value = null
}

const submitOrderFromDetails = () => {
    // Select the table to load it into cart
    const table = tables.value.find(t => t.table_name === selectedTableOrder.value.tableName)
    if (table) {
        emit('table-selected', table)
    }
    closeDetailsModal()
}

const checkoutFromDetails = () => {
    // Select the table to load it into cart + trigger checkout
    const table = tables.value.find(t => t.table_name === selectedTableOrder.value.tableName)
    if (table) {
        emit('checkout-table', table)
    }
    closeDetailsModal()
}

onMounted(fetchData)
</script>

<style scoped>
.animate-slide-left {
  animation: slideLeft 0.3s ease-out;
}

@keyframes slideLeft {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}
</style>
