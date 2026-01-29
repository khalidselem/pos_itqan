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
                <span class="text-gray-600">{{ __('Available') }}</span>
            </div>
            <div class="flex items-center gap-1.5">
                <span class="w-3 h-3 rounded-full bg-orange-500"></span>
                <span class="text-gray-600">{{ __('Reserved') }}</span>
            </div>
            <div class="flex items-center gap-1.5">
                <span class="w-3 h-3 rounded-full bg-red-500"></span>
                <span class="text-gray-600">{{ __('Occupied') }}</span>
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
                        <div class="text-[10px] font-bold truncate opacity-80">{{ table.current_customer || __('No Customer') }}</div>
                        <div class="text-[10px] truncate opacity-60">{{ table.current_order }}</div>
                    </div>

                    <div class="mt-auto flex justify-between items-center">
                        <span class="px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider bg-white/30">
                            {{ table.status }}
                        </span>
                    </div>
                </div>

                <!-- Quick Action Overlay -->
                <!-- <div class="absolute inset-0 bg-black/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl pointer-events-none"></div> -->
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

const emit = defineEmits(['close', 'table-selected'])
const { formatCurrency } = useFormatters()

const tables = ref([])
const zones = ref([])
const loading = ref(true)
const selectedZone = ref('All')

const fetchData = async () => {
    loading.value = true
    try {
        const [tablesRes, zonesRes] = await Promise.all([
            call('pos_itqan.api.tables.get_tables'),
            call('pos_itqan.api.tables.get_zones')
        ])
        tables.value = tablesRes || []
        zones.value = zonesRes || []
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

const getStatusClasses = (status) => {
    switch (status) {
        case 'Available': return 'bg-white border-emerald-100 text-emerald-700'
        case 'Occupied': return 'bg-red-50 border-red-200 text-red-700'
        case 'Reserved': return 'bg-orange-50 border-orange-200 text-orange-700'
        case 'Disabled': return 'bg-gray-100 border-gray-200 text-gray-400 grayscale'
        default: return 'bg-white border-gray-100 text-gray-500'
    }
}

const onTableClick = (table) => {
    if (table.status === 'Disabled') return
    emit('table-selected', table)
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
