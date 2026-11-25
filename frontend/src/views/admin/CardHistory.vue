<script setup>
import { ref } from 'vue'
import api from '@/api'

const searchCode = ref('')
const coupon = ref(null)
const history = ref([])
const loading = ref(false)
const error = ref('')
const retireOpen = ref(false)
const retireReason = ref('')
const retireLoading = ref(false)
const retireError = ref('')

function formatPrague(iso) {
  return new Date(iso).toLocaleString('cs-CZ', { timeZone: 'Europe/Prague' })
}

const STATE_LABELS = {
  VOLNA: 'Volná',
  K_UPLATNENI: 'Vydaná',
  VYRAZENA: 'Vyřazená',
}

const STATE_CLASSES = {
  VOLNA: 'bg-blue-100 text-blue-800',
  K_UPLATNENI: 'bg-orange-100 text-orange-800',
  VYRAZENA: 'bg-red-100 text-red-800',
}

async function search() {
  const code = searchCode.value.trim()
  if (!code) return
  loading.value = true
  error.value = ''
  coupon.value = null
  history.value = []
  try {
    const [r1, r2] = await Promise.all([
      api.get(`/coupons/${code}`),
      api.get(`/coupons/${code}/history`),
    ])
    coupon.value = r1.data
    history.value = r2.data
  } catch (e) {
    if (e.response?.status === 404) {
      error.value = 'Kartička nebyla nalezena'
    } else {
      error.value = 'Chyba při načítání'
    }
  } finally {
    loading.value = false
  }
}

async function retire() {
  retireLoading.value = true
  retireError.value = ''
  try {
    await api.post(`/coupons/${coupon.value.code}/retire`, { reason: retireReason.value })
    retireOpen.value = false
    retireReason.value = ''
    await search()
  } catch (e) {
    const detail = e.response?.data?.detail
    retireError.value = typeof detail === 'string' ? detail : 'Vyřazení selhalo'
  } finally {
    retireLoading.value = false
  }
}
</script>

<template>
  <div class="p-6 max-w-3xl mx-auto">

    <!-- Vyhledávání -->
    <form @submit.prevent="search" class="flex gap-3 mb-6">
      <input
        v-model="searchCode"
        type="text"
        placeholder="Kód kartičky (4 číslice)"
        maxlength="4"
        class="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm font-mono
               focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
      />
      <button
        type="submit"
        :disabled="loading || !searchCode.trim()"
        class="px-5 py-2 bg-[#111111] hover:bg-gray-800 text-white font-semibold text-sm
               rounded-lg transition disabled:opacity-50"
      >
        {{ loading ? 'Hledám…' : 'Hledat' }}
      </button>
    </form>

    <!-- Chyba -->
    <p v-if="error" class="text-red-600 text-sm mb-4">{{ error }}</p>

    <!-- Detail kartičky -->
    <template v-if="coupon">

      <div class="bg-white rounded-xl border border-gray-200 p-5 mb-4 flex items-center justify-between flex-wrap gap-3">
        <div class="flex items-center gap-4">
          <span class="font-mono text-2xl font-black text-gray-900">{{ coupon.code }}</span>
          <span
            class="px-3 py-1 rounded-full text-xs font-bold"
            :class="STATE_CLASSES[coupon.state] ?? 'bg-gray-100 text-gray-600'"
          >
            {{ STATE_LABELS[coupon.state] ?? coupon.state }}
          </span>
        </div>
        <button
          v-if="coupon.state !== 'VYRAZENA'"
          @click="retireOpen = true"
          class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold
                 rounded-lg transition"
        >
          Vyřadit kartu
        </button>
      </div>

      <!-- Timeline -->
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <h2 class="text-sm font-semibold text-gray-700 px-5 py-3 border-b border-gray-100">
          Historie
        </h2>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th class="text-left px-4 py-3 font-medium">Čas (Praha)</th>
                <th class="text-left px-4 py-3 font-medium">Akce</th>
                <th class="text-left px-4 py-3 font-medium">Výsledek</th>
                <th class="text-left px-4 py-3 font-medium">Účet</th>
                <th class="text-left px-4 py-3 font-medium">Pobočka</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="entry in history"
                :key="entry.id"
                class="border-t border-gray-100"
                :class="entry.is_suspicious ? 'bg-red-50 border-l-4 border-l-red-400' : 'even:bg-gray-50'"
              >
                <td class="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                  {{ formatPrague(entry.server_time) }}
                </td>
                <td class="px-4 py-3 font-medium">{{ entry.action }}</td>
                <td class="px-4 py-3">
                  {{ entry.result }}
                  <span v-if="entry.is_suspicious && entry.suspicious_reason"
                        class="block text-xs italic text-red-500 mt-0.5">
                    {{ entry.suspicious_reason }}
                  </span>
                </td>
                <td class="px-4 py-3">{{ entry.account_login }}</td>
                <td class="px-4 py-3 text-gray-600">{{ entry.restaurant_name ?? '—' }}</td>
              </tr>
              <tr v-if="history.length === 0">
                <td colspan="5" class="px-4 py-8 text-center text-gray-400">
                  Žádné záznamy
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </template>

    <!-- Retire modal -->
    <div v-if="retireOpen"
         class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div class="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-6 flex flex-col gap-4">
        <h2 class="text-lg font-bold">Vyřadit kartu {{ coupon?.code }}</h2>
        <p class="text-sm text-gray-500">
          Zadejte důvod vyřazení. Akce je nevratná.
        </p>
        <textarea
          v-model="retireReason"
          rows="3"
          placeholder="Důvod vyřazení…"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                 focus:outline-none focus:ring-2 focus:ring-red-400 resize-none"
        ></textarea>
        <p v-if="retireError" class="text-red-600 text-sm">{{ retireError }}</p>
        <div class="flex gap-3">
          <button
            @click="retireOpen = false; retireReason = ''; retireError = ''"
            class="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-sm transition"
          >
            Zrušit
          </button>
          <button
            @click="retire"
            :disabled="retireReason.trim() === '' || retireLoading"
            class="flex-1 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl
                   font-bold text-sm transition disabled:opacity-50"
          >
            {{ retireLoading ? 'Ukládám…' : 'Vyřadit' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
