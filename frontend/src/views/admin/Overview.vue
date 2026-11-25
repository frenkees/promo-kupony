<script setup>
import { ref, watch, onMounted } from 'vue'
import api from '@/api'

const data = ref(null)
const loading = ref(false)
const error = ref('')
const dateFrom = ref('')
const dateTo = ref('')

function formatPrague(iso) {
  return new Date(iso).toLocaleString('cs-CZ', { timeZone: 'Europe/Prague' })
}

// Lokální datum z <input type="date"> → UTC ISO. Browser parsuje 'YYYY-MM-DDTHH:MM:SS'
// jako lokální čas, .toISOString() to převede na UTC, takže backend dostane správný range.
function localDateStartUTC(d) { return new Date(d + 'T00:00:00').toISOString() }
function localDateEndUTC(d)   { return new Date(d + 'T23:59:59.999').toISOString() }

async function fetchOverview() {
  loading.value = true
  error.value = ''
  try {
    const params = {}
    if (dateFrom.value) params.date_from = localDateStartUTC(dateFrom.value)
    if (dateTo.value)   params.date_to   = localDateEndUTC(dateTo.value)
    const { data: d } = await api.get('/dashboard/overview', { params })
    data.value = d
  } catch {
    error.value = 'Nepodařilo se načíst přehled'
  } finally {
    loading.value = false
  }
}

watch([dateFrom, dateTo], fetchOverview)
onMounted(fetchOverview)
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">

    <!-- Filtr období -->
    <div class="flex flex-wrap items-center gap-3 mb-6">
      <label class="text-sm font-medium text-gray-600">Období:</label>
      <input
        v-model="dateFrom"
        type="date"
        class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
      />
      <span class="text-gray-400 text-sm">–</span>
      <input
        v-model="dateTo"
        type="date"
        class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
      />
      <button
        v-if="dateFrom || dateTo"
        @click="dateFrom = ''; dateTo = ''"
        class="text-xs text-gray-400 hover:text-gray-600"
      >
        Zrušit filtr
      </button>
    </div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Načítám…</div>
    <div v-else-if="error" class="text-red-600 text-center py-12">{{ error }}</div>

    <template v-else-if="data">

      <!-- KPI karty -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div class="bg-white rounded-xl border border-gray-200 p-6">
          <p class="text-sm text-gray-500 mb-1">Otevřený závazek</p>
          <p class="text-4xl font-black text-gray-900">{{ data.open_liability }}</p>
          <p class="text-xs text-gray-400 mt-1">kartiček vydáno, čeká na uplatnění</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-6">
          <p class="text-sm text-gray-500 mb-1">Míra uplatnění</p>
          <p class="text-4xl font-black text-gray-900">
            {{ (data.redemption_rate * 100).toFixed(1) }} %
          </p>
          <p class="text-xs text-gray-400 mt-1">z celkově vydaných kartiček</p>
        </div>
      </div>

      <!-- Fond -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h2 class="text-sm font-semibold text-gray-700 mb-3">Stav fondu</h2>
        <div class="flex flex-wrap gap-4">
          <div class="flex items-center gap-2">
            <span class="inline-block w-3 h-3 rounded-full bg-blue-500"></span>
            <span class="text-sm text-gray-600">Volná:</span>
            <span class="font-bold text-gray-900">{{ data.fund['VOLNA'] ?? 0 }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="inline-block w-3 h-3 rounded-full bg-orange-400"></span>
            <span class="text-sm text-gray-600">Vydaná:</span>
            <span class="font-bold text-gray-900">{{ data.fund['K_UPLATNENI'] ?? 0 }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="inline-block w-3 h-3 rounded-full bg-red-500"></span>
            <span class="text-sm text-gray-600">Vyřazená:</span>
            <span class="font-bold text-gray-900">{{ data.fund['VYRAZENA'] ?? 0 }}</span>
          </div>
        </div>
      </div>

      <!-- Tabulka poboček -->
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <h2 class="text-sm font-semibold text-gray-700 px-5 py-3 border-b border-gray-100">
          Aktivita poboček
        </h2>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th class="text-left px-5 py-3 font-medium">Pobočka</th>
                <th class="text-right px-5 py-3 font-medium">Vydáno</th>
                <th class="text-right px-5 py-3 font-medium">Uplatněno</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in data.by_restaurant"
                :key="r.restaurant_id"
                class="border-t border-gray-100 even:bg-gray-50"
              >
                <td class="px-5 py-3">{{ r.name }}</td>
                <td class="px-5 py-3 text-right tabular-nums">{{ r.issued }}</td>
                <td class="px-5 py-3 text-right tabular-nums">{{ r.redeemed }}</td>
              </tr>
              <tr v-if="data.by_restaurant.length === 0">
                <td colspan="3" class="px-5 py-6 text-center text-gray-400">Žádná data</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </template>
  </div>
</template>
