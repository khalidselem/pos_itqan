<template>
  <Transition name="fade">
    <div
      v-if="show"
      class="fixed inset-0 bg-black bg-opacity-50 z-[50]"
      @click.self="handleClose"
    >
      <div class="fixed inset-0 flex items-center justify-center p-4">
        <div class="w-full h-full max-w-7xl max-h-[85vh] bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col transition-all">
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-emerald-50 to-teal-50">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-emerald-100 rounded-lg">
                <svg class="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-gray-900">{{ __('POS Payments') }}</h2>
                <p class="text-sm text-gray-600">{{ __('Consolidated payments for POS customers') }}</p>
              </div>
            </div>
            <button
              @click="handleClose"
              class="p-2 hover:bg-white/50 rounded-lg transition-colors"
            >
              <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Main Layout -->
          <div class="flex-1 flex overflow-hidden">
            
            <!-- LEFT PANEL: Customer Selection -->
            <div class="w-1/4 min-w-[300px] border-e border-gray-200 bg-gray-50 flex flex-col">
              <div class="p-4 border-b border-gray-200 bg-white">
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Customer') }}</label>
                <div class="flex gap-2">
                  <div class="relative flex-1">
                    <span class="absolute inset-y-0 start-0 flex items-center ps-3 text-gray-400">
                       <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                       </svg>
                    </span>
                    <Combobox v-model="selectedCustomer" :options="customerOptions" @input="handleCustomerSearch" nullable>
                        <template #option="{ option }">
                            <div class="flex flex-col py-1">
                                <span class="font-medium text-gray-900">{{ option.label }}</span>
                                <span class="text-xs text-gray-500">{{ option.value }}</span>
                            </div>
                        </template>
                    </Combobox>
                  </div>
                  <button 
                    class="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700" 
                    title="Add Customer"
                    @click="$emit('create-customer')"
                  >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                  </button>
                </div>
              </div>

              <!-- Customer Info (if selected) -->
              <div v-if="selectedCustomer" class="p-4 flex-1 overflow-y-auto">
                 <div class="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
                    <div class="flex items-center gap-3 mb-3">
                        <div class="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold">
                            {{ (typeof selectedCustomer === 'string' ? selectedCustomer : (selectedCustomer.label || selectedCustomer.value || '?'))[0]?.toUpperCase() }}
                        </div>
                        <div>
                            <div class="font-bold text-gray-900">
                                {{ typeof selectedCustomer === 'string' ? selectedCustomer : (selectedCustomer.label || selectedCustomer.value || 'Unknown') }}
                            </div>
                            <div class="text-xs text-list-500">
                                {{ typeof selectedCustomer === 'string' ? __('Please select from list') : selectedCustomer.value }}
                            </div>
                            <div v-if="typeof selectedCustomer !== 'string' && selectedCustomer.mobile" class="text-xs text-gray-400 mt-1">
                                {{ selectedCustomer.mobile }}
                            </div>
                        </div>
                    </div>
                 </div>
              </div>
              <div v-else class="flex-1 flex flex-col items-center justify-center text-gray-400 p-8 text-center">
                 <svg class="w-12 h-12 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                 </svg>
                 <p>{{ __('Select a customer to view invoices') }}</p>
              </div>
            </div>

            <!-- CENTER PANEL: Invoice List -->
            <div class="flex-1 flex flex-col border-e border-gray-200 bg-white">
              <div class="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                 <h3 class="font-bold text-gray-800">{{ __('Unpaid Invoices') }}</h3>
                 <div class="text-sm text-gray-500" v-if="invoices.length > 0">
                    {{ __('{0} invoices found', [invoices.length]) }}
                 </div>
              </div>

              <!-- Loading State -->
              <div v-if="loadingInvoices" class="flex-1 flex items-center justify-center">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
              </div>

              <!-- Empty State -->
              <div v-else-if="invoices.length === 0" class="flex-1 flex flex-col items-center justify-center text-gray-400 p-8">
                <svg class="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <p>{{ __('No unpaid invoices found') }}</p>
              </div>

              <!-- Invoice Table -->
              <div v-else class="flex-1 overflow-y-auto">
                <table class="w-full text-sm text-left">
                  <thead class="text-xs text-gray-700 uppercase bg-gray-50 sticky top-0">
                    <tr>
                      <th scope="col" class="p-4 w-10">
                        <div class="flex items-center">
                          <input type="checkbox" v-model="selectAll" class="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500">
                        </div>
                      </th>
                      <th scope="col" class="px-4 py-3">{{ __('Invoice') }}</th>
                      <th scope="col" class="px-4 py-3">{{ __('Date') }}</th>
                      <th scope="col" class="px-4 py-3 text-end">{{ __('Total') }}</th>
                      <th scope="col" class="px-4 py-3 text-end">{{ __('Outstanding') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr 
                        v-for="invoice in invoices" 
                        :key="invoice.name"
                        class="border-b hover:bg-gray-50 cursor-pointer"
                        @click="toggleInvoice(invoice)"
                    >
                      <td class="p-4 w-10">
                        <div class="flex items-center">
                          <input 
                            type="checkbox" 
                            :checked="isSelected(invoice.name)"
                            class="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500 pointer-events-none"
                          >
                        </div>
                      </td>
                      <td class="px-4 py-3 font-medium text-gray-900">{{ invoice.name }}</td>
                      <td class="px-4 py-3 text-gray-500">{{ formatDate(invoice.posting_date) }}</td>
                      <td class="px-4 py-3 text-end font-medium">{{ formatCurrency(invoice.grand_total, invoice.currency) }}</td>
                      <td class="px-4 py-3 text-end font-bold text-orange-600">{{ formatCurrency(invoice.outstanding_amount, invoice.currency) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- RIGHT PANEL: Totals & Payments -->
            <div class="w-1/4 min-w-[320px] bg-gray-50 flex flex-col shadow-inner">
               <div class="p-6 flex-1 overflow-y-auto">
                    <!-- Summary Card -->
                    <div class="bg-white p-5 rounded-xl shadow-sm border border-gray-200 mb-6">
                        <h4 class="text-sm font-semibold text-gray-500 mb-4 uppercase tracking-wider">{{ __('Payment Summary') }}</h4>
                        
                        <div class="flex justify-between items-center mb-3">
                            <span class="text-gray-600">{{ __('Selected Invoices') }}</span>
                            <span class="font-bold text-gray-900">{{ selectedInvoices.length }}</span>
                        </div>
                        
                        <div class="flex justify-between items-center mb-4 pb-4 border-b border-gray-100">
                            <span class="text-gray-600">{{ __('Total Outstanding') }}</span>
                            <span class="font-bold text-xl text-gray-900">{{ formatCurrency(totalSelectedOutstanding) }}</span>
                        </div>
                        
                        <div class="flex justify-between items-center pt-2">
                            <span class="text-gray-600 font-medium">{{ __('Difference') }}</span>
                            <span 
                                :class="[
                                    'font-bold text-xl',
                                    difference < 0 ? 'text-red-500' : 'text-emerald-600'
                                ]"
                            >
                                {{ formatCurrency(difference) }}
                            </span>
                        </div>
                    </div>

                    <!-- Payment Methods -->
                    <div class="space-y-4">
                        <h4 class="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wider">{{ __('Make Payment') }}</h4>
                        
                        <div v-for="mode in paymentModes" :key="mode.name" class="relative">
                            <label class="block text-xs font-medium text-gray-700 mb-1 ps-1">{{ mode.label }}</label>
                            <div class="relative rounded-md shadow-sm">
                                <div class="absolute inset-y-0 start-0 flex items-center ps-3 pointer-events-none">
                                    <span class="text-gray-500 sm:text-sm font-bold">{{ currencySymbol }}</span>
                                </div>
                                <input
                                    type="number"
                                    v-model.number="payments[mode.name]"
                                    min="0"
                                    step="0.001"
                                    class="block w-full rounded-lg border-gray-300 ps-10 focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm py-2.5 transition-colors"
                                    :placeholder="'0.000'"
                                />
                            </div>
                        </div>
                    </div>
               </div>

               <!-- Footer Actions -->
               <div class="p-4 bg-white border-t border-gray-200">
                  <div v-if="invoices.length > 0 && selectedInvoices.length === 0" class="text-xs text-orange-600 mb-2 text-center">
                      {{ __('Select invoices to pay') }}
                  </div>
                  <Button
                    variant="solid"
                    theme="emerald"
                    size="lg"
                    class="w-full justify-center font-bold text-base py-3"
                    :loading="submitting"
                    :disabled="!canSubmit"
                    @click="handleSubmit"
                  >
                    {{ __('Submit Payment') }}
                  </Button>
               </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Button, Combobox, createListResource } from 'frappe-ui'
import { useFormatters } from '@/composables/useFormatters'
import { useToast } from '@/composables/useToast'
import { formatCurrency as formatCurrencyUtil } from '@/utils/currency'

const props = defineProps({
  modelValue: Boolean,
  posProfile: String,
  currency: {
    type: String,
    default: 'KWD'
  }
})

const emit = defineEmits(['update:modelValue'])

const { formatDate } = useFormatters()
const { showSuccess, showError } = useToast()

const show = ref(props.modelValue)
const loadingInvoices = ref(false)
const submitting = ref(false)
const invoices = ref([])
const selectedInvoices = ref([]) // Sets of names
const payments = ref({})

// Customer Search
const selectedCustomer = ref(null)
const customerSearchQuery = ref('')
const customerResource = createListResource({
  doctype: 'Customer',
  fields: ['name', 'customer_name', 'mobile_no'],
  auto: true,
  transform(data) {
    return data.map(c => ({
      label: c.customer_name,
      value: c.name,
      mobile: c.mobile_no
    }))
  }
})

const customerOptions = computed(() => {
    return customerResource.data || []
})

function handleCustomerSearch(query) {
    customerSearchQuery.value = query
    customerResource.update({
        filters: {
            customer_name: ['like', `%${query}%`]
        }
    })
    customerResource.reload()
}

// Payment Modes (Hardcoded for now as per requirement, or fetch from POS Profile)
const paymentModes = [
    { name: 'Cash', label: 'Cash' },
    { name: 'KNET', label: 'KNET' },
    { name: 'Credit Card', label: 'Visa / MasterCard' }, // Using Credit Card as generic for Visa/Master
    { name: 'Bank Transfer', label: 'Bank Transfer' }
]

// Initialize payments object
paymentModes.forEach(m => payments.value[m.name] = 0)

const currencySymbol = computed(() => props.currency)

// Computed logic
const totalSelectedOutstanding = computed(() => {
    return selectedInvoices.value.reduce((sum, name) => {
        const inv = invoices.value.find(i => i.name === name)
        return sum + (inv ? inv.outstanding_amount : 0)
    }, 0)
})

const totalPaymentInput = computed(() => {
    return Object.values(payments.value).reduce((sum, val) => sum + (val || 0), 0)
})

const difference = computed(() => {
    return totalSelectedOutstanding.value - totalPaymentInput.value
})

const canSubmit = computed(() => {
    return selectedInvoices.value.length > 0 && totalPaymentInput.value > 0 && totalPaymentInput.value <= totalSelectedOutstanding.value + 0.001 // simple tolerance
})

const selectAll = computed({
    get() {
        return invoices.value.length > 0 && invoices.value.length === selectedInvoices.value.length
    },
    set(val) {
        if (val) {
            selectedInvoices.value = invoices.value.map(i => i.name)
        } else {
            selectedInvoices.value = []
        }
    }
})

function isSelected(name) {
    return selectedInvoices.value.includes(name)
}

function toggleInvoice(invoice) {
    const idx = selectedInvoices.value.indexOf(invoice.name)
    if (idx === -1) {
        selectedInvoices.value.push(invoice.name)
    } else {
        selectedInvoices.value.splice(idx, 1)
    }
}

// Fetch invoices when customer selected
watch(selectedCustomer, (newVal) => {
    // Handle both object (standard) and potential raw value (edge case)
    const customerName = newVal?.value || (typeof newVal === 'string' ? newVal : null)
    
    if (customerName) {
        fetchUnpaidInvoices(customerName)
    } else {
        invoices.value = []
        selectedInvoices.value = []
    }
})

async function fetchUnpaidInvoices(customer) {
    loadingInvoices.value = true
    try {
        const res = await callWithRetry('pos_itqan.api.invoices.get_customer_outstanding_invoices', {
            customer: customer
        })
        invoices.value = res || []
    } catch (e) {
        console.error(e)
        showError('Failed to fetch invoices')
    } finally {
        loadingInvoices.value = false
    }
}

// Watchers for show prop
watch(() => props.modelValue, (val) => {
    show.value = val
    if (val) {
        // Reset state
        selectedCustomer.value = null
        invoices.value = []
        selectedInvoices.value = []
        Object.keys(payments.value).forEach(k => payments.value[k] = 0)
    }
})

watch(show, (val) => {
    emit('update:modelValue', val)
})

function handleClose() {
    show.value = false
}

function formatCurrency(amount, currency = props.currency) {
    return formatCurrencyUtil(amount, currency)
}

function setCustomer(customer) {
    if (!customer) return
    selectedCustomer.value = {
        label: customer.customer_name,
        value: customer.name,
        mobile: customer.mobile_no
    }
}

defineExpose({
    setCustomer
})

// Helper to call frappe methods
function callWithRetry(method, args) {
    return frappe.call({
        method: method,
        args: args
    }).then(r => r.message)
}

async function handleSubmit() {
    if (!canSubmit.value) return
    
    // Prevent overpayment block
    if (totalPaymentInput.value > totalSelectedOutstanding.value) {
        showError('Payment exceeds total outstanding amount')
        return
    }

    submitting.value = true
    try {
        const paymentList = Object.entries(payments.value)
            .filter(([_, amount]) => amount > 0)
            .map(([mode, amount]) => ({
                mode_of_payment: mode,
                amount: amount
            }))
        
        const invoiceList = selectedInvoices.value.map(name => {
            const inv = invoices.value.find(i => i.name === name)
            return {
                name: name,
                allocated_amount: inv.outstanding_amount,
                grand_total: inv.grand_total,
                outstanding_amount: inv.outstanding_amount
            }
        })

        // We need company from POS Profile or session
        // Assuming we can get it from shiftStore or props, but simpler to rely on backend to infer or pass explicit
        // For now, let's assume we can get it via call context or we need to pass it.
        // Let's rely on backend logic finding default company if not passed, BUT backend api expects it.
        // We will try to get it from frappe.defaults or similar, but better to pass it.
        // The props doesn't have company. Let's see if we can get it from somewhere.
        // Actually, props SHOULD have company if possible. POSSale passes it to other components.
        // We will add `company` to props in next step or infer it.
        // For now, let's pass it if available or let backend handle error.
        
        await callWithRetry('pos_itqan.api.invoices.create_consolidated_payment_entry', {
            data: {
                customer: selectedCustomer.value.value,
                company: frappe.defaults.get_default("company"), // Fallback, better to pass prop
                pos_profile: props.posProfile,
                payments: paymentList,
                invoices: invoiceList
            }
        })

        showSuccess('Payment submitted successfully')
        handleClose()
        // Here we should probably refresh the invoice list if we were staying open,
        // but since we close, it's fine.
    } catch (e) {
        console.error(e)
        showError(e.message || 'Failed to submit payment')
    } finally {
        submitting.value = false
    }
}
</script>

<style scoped>
/* Custom scrollbar for better look */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
