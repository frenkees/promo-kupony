<script setup>
import { ref, watch, onMounted } from 'vue'
import api from '@/api'

const rows = ref([])
const loading = ref(false)
const error = ref('')
const restaurants = ref([])
const filterRestaurant = ref('')
const dateFrom = ref('')
const dateTo = ref('')

function formatPrague(iso) {
  return new Date(iso).toLocaleString('cs-CZ', { timeZone: 'Europe/Prague' })
}

// Lokální datum z <input type="date"> → UTC ISO (viz Overview.vue).
function localDateStartUTC(d) { return new Date(d + 'T00:00:00').toISOString() }
function localDateEndUTC(d)   { return new Date(d + 'T23:59:59.999').toISOString() }

async function fetchRestaurants() {
  try {
    const { data } = await api.get('/restaurants')
    restaurants.value = data
  } catch {
    // filtr bez poboček je stále použitelný
  }
}

async function fetchSuspicious() {
  loading.value = true
  error.value = ''
  try {
    const params = {}
    if (filterRestaurant.value) params.restaurant_id = filterRestaurant.value
    if (dateFrom.value) params.date_from = localDateStartUTC(dateFrom.value)
    if (dateTo.value)   params.date_to   = localDateEndUTC(dateTo.value)
    const { data } = await api.get('/dashboard/suspicious', { params })
    rows.value = data
  } catch {
    error.value = 'Nepodařilo se načíst podezřelé akce'
  } finally {
    loading.value = false
  }
}

watch([filterRestaurant, dateFrom, dateTo], fetchSuspicious)

onMounted(() => {
  fetchRestaurants()
  fetchSuspicious()
})
</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">

    <!-- Filtry -->
    <div class="flex flex-wrap items-center gap-3 mb-6">
      <select
        v-model="filterRestaurant"
        class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
      >
        <option value="">Všechny pobočky</option>
        <option v-for="r in restaurants" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>
      <label class="text-sm font-medium text-gray-600">Od:</label>
      <input
        v-model="dateFrom"
        type="date"
        class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
      />
      <label class="text-sm font-medium text-gray-600">Do:</label>
      <input
        v-model="dateTo"
        type="date"
        class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
      />
      <button
        v-if="filterRestaurant || dateFrom || dateTo"
        @click="filterRestaurant = ''; dateFrom = ''; dateTo = ''"
        class="text-xs text-gray-400 hover:text-gray-600"
      >
        Zrušit filtry
      </button>
    </div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Načítám…</div>
    <div v-else-if="error" class="text-red-600 text-center py-12">{{ error }}</div>

    <template v-else>
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-gray-700">Podezřelé akce</h2>
          <span class="text-xs text-gray-400">{{ rows.length }} záznamů</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th class="text-left px-4 py-3 font-medium">Čas (Praha)</th>
                <th class="text-left px-4 py-3 font-medium">Kód</th>
                <th class="text-left px-4 py-3 font-medium">Akce</th>
                <th class="text-left px-4 py-3 font-medium">Výsledek</th>
                <th class="text-left px-4 py-3 font-medium">Účet</th>
                <th class="text-left px-4 py-3 font-medium">Pobočka</th>
                <th class="text-left px-4 py-3 font-medium">Důvod</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in rows"
                :key="row.id"
                class="border-t border-gray-100 bg-red-50 border-l-4 border-l-red-400"
              >
                <td class="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                  {{ formatPrague(row.server_time) }}
                </td>
                <td class="px-4 py-3 font-mono font-bold">{{ row.coupon_code }}</td>
                <td class="px-4 py-3">{{ row.action }}</td>
                <td class="px-4 py-3">{{ row.result }}</td>
                <td class="px-4 py-3">{{ row.account_login }}</td>
                <td class="px-4 py-3 text-gray-600">{{ row.restaurant_name ?? '—' }}</td>
                <td class="px-4 py-3 italic text-gray-500 text-xs">
                  {{ row.suspicious_reason ?? '—' }}
                </td>
              </tr>
              <tr v-if="rows.length === 0">
                <td colspan="7" class="px-4 py-10 text-center text-gray-400">
                  Žádné podezřelé akce
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

  </div>
</template>
