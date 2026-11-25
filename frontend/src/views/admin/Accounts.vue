<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'

const rows = ref([])
const loading = ref(false)
const restaurants = ref([])

const createOpen = ref(false)
const createForm = ref({ login: '', password: '', role: 'operator', restaurant_id: '' })
const createLoading = ref(false)
const createError = ref('')

const resetOpen = ref(false)
const resetRow = ref(null)
const newPassword = ref('')
const resetLoading = ref(false)
const resetError = ref('')

const ROLE_LABELS = { operator: 'Operátor', manager: 'Manažer', master: 'Master' }
const ROLE_CLASSES = {
  operator: 'bg-gray-100 text-gray-700',
  manager: 'bg-blue-100 text-blue-700',
  master: 'bg-purple-100 text-purple-700',
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('cs-CZ', { timeZone: 'Europe/Prague' })
}

async function load() {
  loading.value = true
  try {
    const [r1, r2] = await Promise.all([
      api.get('/accounts'),
      api.get('/restaurants'),
    ])
    rows.value = r1.data
    restaurants.value = r2.data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createForm.value = { login: '', password: '', role: 'operator', restaurant_id: '' }
  createError.value = ''
  createOpen.value = true
}

async function doCreate() {
  createLoading.value = true
  createError.value = ''
  try {
    const body = {
      login: createForm.value.login,
      password: createForm.value.password,
      role: createForm.value.role,
    }
    if (createForm.value.role === 'operator' && createForm.value.restaurant_id) {
      body.restaurant_id = Number(createForm.value.restaurant_id)
    }
    await api.post('/accounts', body)
    createOpen.value = false
    await load()
  } catch (e) {
    const detail = e.response?.data?.detail
    if (Array.isArray(detail)) {
      createError.value = detail.map(d => d.msg).join(', ')
    } else {
      createError.value = typeof detail === 'string' ? detail : 'Vytvoření selhalo'
    }
  } finally {
    createLoading.value = false
  }
}

function openReset(row) {
  resetRow.value = row
  newPassword.value = ''
  resetError.value = ''
  resetOpen.value = true
}

async function doReset() {
  resetLoading.value = true
  resetError.value = ''
  try {
    await api.post(`/accounts/${resetRow.value.id}/reset-password`, {
      new_password: newPassword.value,
    })
    resetOpen.value = false
    await load()
  } catch (e) {
    const detail = e.response?.data?.detail
    resetError.value = typeof detail === 'string' ? detail : 'Reset selhalo'
  } finally {
    resetLoading.value = false
  }
}

async function toggleActive(row) {
  try {
    const { data } = await api.post(`/accounts/${row.id}/toggle-active`)
    row.active = data.active
  } catch {
    // tiché selhání — reload pro konzistenci
    await load()
  }
}

const createRestaurantRequired = computed(
  () => createForm.value.role === 'operator'
)

onMounted(load)
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">

    <div class="flex items-center justify-between mb-4">
      <h2 class="text-base font-semibold text-gray-800">Účty</h2>
      <button
        @click="openCreate"
        class="px-4 py-2 bg-[#111111] hover:bg-gray-800 text-white text-sm font-semibold rounded-lg transition"
      >
        + Nový účet
      </button>
    </div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Načítám…</div>

    <div v-else class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th class="text-left px-4 py-3 font-medium">Login</th>
              <th class="text-left px-4 py-3 font-medium">Role</th>
              <th class="text-left px-4 py-3 font-medium">Pobočka</th>
              <th class="text-left px-4 py-3 font-medium">Vytvořeno</th>
              <th class="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in rows"
              :key="row.id"
              class="border-t border-gray-100 even:bg-gray-50 transition"
              :class="{ 'opacity-50': !row.active }"
            >
              <td class="px-4 py-3 font-medium">
                {{ row.login }}
                <span v-if="row.must_change_password"
                      class="ml-1 text-xs text-amber-600" title="Musí změnit heslo">⚠</span>
              </td>
              <td class="px-4 py-3">
                <span
                  class="px-2 py-0.5 rounded-full text-xs font-semibold"
                  :class="ROLE_CLASSES[row.role] ?? 'bg-gray-100 text-gray-600'"
                >
                  {{ ROLE_LABELS[row.role] ?? row.role }}
                </span>
              </td>
              <td class="px-4 py-3 text-gray-500">{{ row.restaurant_name ?? '—' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ formatDate(row.created_at) }}</td>
              <td class="px-4 py-3">
                <div class="flex gap-2 justify-end">
                  <button
                    @click="openReset(row)"
                    class="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-xs font-medium transition"
                  >
                    Reset hesla
                  </button>
                  <button
                    @click="toggleActive(row)"
                    class="px-3 py-1 rounded text-xs font-medium transition"
                    :class="row.active
                      ? 'bg-red-50 hover:bg-red-100 text-red-700'
                      : 'bg-green-50 hover:bg-green-100 text-green-700'"
                  >
                    {{ row.active ? 'Deaktivovat' : 'Aktivovat' }}
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="rows.length === 0">
              <td colspan="5" class="px-4 py-10 text-center text-gray-400">Žádné účty</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create modal -->
    <div v-if="createOpen" class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div class="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-6 flex flex-col gap-4">
        <h2 class="text-lg font-bold">Nový účet</h2>

        <div class="flex flex-col gap-3">
          <input
            v-model="createForm.login"
            type="text"
            placeholder="Login"
            autocomplete="off"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                   focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
          />
          <input
            v-model="createForm.password"
            type="password"
            placeholder="Heslo (min. 8 znaků)"
            minlength="8"
            autocomplete="new-password"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                   focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
          />
          <select
            v-model="createForm.role"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                   focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
          >
            <option value="operator">Operátor</option>
            <option value="manager">Manažer</option>
            <option value="master">Master</option>
          </select>
          <select
            v-if="createRestaurantRequired"
            v-model="createForm.restaurant_id"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                   focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
          >
            <option value="">— Vyberte pobočku —</option>
            <option v-for="r in restaurants" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </div>

        <p class="text-xs text-gray-400">
          Nový účet bude při prvním přihlášení požádán o změnu hesla.
        </p>

        <p v-if="createError" class="text-red-600 text-sm">{{ createError }}</p>

        <div class="flex gap-3">
          <button
            @click="createOpen = false"
            class="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-sm transition"
          >
            Zrušit
          </button>
          <button
            @click="doCreate"
            :disabled="createForm.login.trim() === ''
              || createForm.password.length < 8
              || (createRestaurantRequired && !createForm.restaurant_id)
              || createLoading"
            class="flex-1 py-3 bg-[#111111] hover:bg-gray-800 text-white rounded-xl
                   font-bold text-sm transition disabled:opacity-50"
          >
            {{ createLoading ? 'Ukládám…' : 'Vytvořit' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Reset password modal -->
    <div v-if="resetOpen" class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div class="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-6 flex flex-col gap-4">
        <h2 class="text-lg font-bold">Reset hesla</h2>
        <p class="text-sm text-gray-500">
          Účet: <strong>{{ resetRow?.login }}</strong>
        </p>
        <input
          v-model="newPassword"
          type="password"
          placeholder="Nové heslo (min. 8 znaků)"
          minlength="8"
          autocomplete="new-password"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                 focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
        />
        <p v-if="resetError" class="text-red-600 text-sm">{{ resetError }}</p>
        <div class="flex gap-3">
          <button
            @click="resetOpen = false"
            class="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-sm transition"
          >
            Zrušit
          </button>
          <button
            @click="doReset"
            :disabled="newPassword.length < 8 || resetLoading"
            class="flex-1 py-3 bg-[#111111] hover:bg-gray-800 text-white rounded-xl
                   font-bold text-sm transition disabled:opacity-50"
          >
            {{ resetLoading ? 'Ukládám…' : 'Nastavit heslo' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
