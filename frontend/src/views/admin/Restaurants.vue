<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'

const rows = ref([])
const loading = ref(false)

const addOpen = ref(false)
const addName = ref('')
const addLoading = ref(false)
const addError = ref('')

const editOpen = ref(false)
const editRow = ref(null)
const editName = ref('')
const editLoading = ref(false)
const editError = ref('')

const deleteOpen = ref(false)
const deleteRow = ref(null)
const deleteLoading = ref(false)
const deleteError = ref('')

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('cs-CZ', { timeZone: 'Europe/Prague' })
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/restaurants')
    rows.value = data
  } finally {
    loading.value = false
  }
}

function openAdd() {
  addName.value = ''
  addError.value = ''
  addOpen.value = true
}

async function doAdd() {
  addLoading.value = true
  addError.value = ''
  try {
    await api.post('/restaurants', { name: addName.value })
    addOpen.value = false
    await load()
  } catch (e) {
    const detail = e.response?.data?.detail
    addError.value = typeof detail === 'string' ? detail : 'Přidání selhalo'
  } finally {
    addLoading.value = false
  }
}

function openEdit(row) {
  editRow.value = row
  editName.value = row.name
  editError.value = ''
  editOpen.value = true
}

async function doEdit() {
  editLoading.value = true
  editError.value = ''
  try {
    await api.put(`/restaurants/${editRow.value.id}`, { name: editName.value })
    editOpen.value = false
    await load()
  } catch (e) {
    const detail = e.response?.data?.detail
    editError.value = typeof detail === 'string' ? detail : 'Úprava selhala'
  } finally {
    editLoading.value = false
  }
}

function openDelete(row) {
  deleteRow.value = row
  deleteError.value = ''
  deleteOpen.value = true
}

async function doDelete() {
  deleteLoading.value = true
  deleteError.value = ''
  try {
    await api.delete(`/restaurants/${deleteRow.value.id}`)
    deleteOpen.value = false
    await load()
  } catch (e) {
    const detail = e.response?.data?.detail
    deleteError.value = typeof detail === 'string' ? detail : 'Smazání selhalo'
  } finally {
    deleteLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="p-6 max-w-3xl mx-auto">

    <div class="flex items-center justify-between mb-4">
      <h2 class="text-base font-semibold text-gray-800">Pobočky</h2>
      <button
        @click="openAdd"
        class="px-4 py-2 bg-[#111111] hover:bg-gray-800 text-white text-sm font-semibold rounded-lg transition"
      >
        + Přidat pobočku
      </button>
    </div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Načítám…</div>

    <div v-else class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th class="text-left px-5 py-3 font-medium w-12">ID</th>
              <th class="text-left px-5 py-3 font-medium">Název</th>
              <th class="text-left px-5 py-3 font-medium">Vytvořeno</th>
              <th class="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in rows"
              :key="r.id"
              class="border-t border-gray-100 even:bg-gray-50"
            >
              <td class="px-5 py-3 text-gray-400 tabular-nums">{{ r.id }}</td>
              <td class="px-5 py-3 font-medium">{{ r.name }}</td>
              <td class="px-5 py-3 text-gray-500">{{ formatDate(r.created_at) }}</td>
              <td class="px-5 py-3">
                <div class="flex gap-2 justify-end">
                  <button
                    @click="openEdit(r)"
                    class="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-xs font-medium transition"
                  >
                    Upravit
                  </button>
                  <button
                    @click="openDelete(r)"
                    class="px-3 py-1 bg-red-50 hover:bg-red-100 text-red-700 rounded text-xs font-medium transition"
                  >
                    Smazat
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="rows.length === 0">
              <td colspan="4" class="px-5 py-10 text-center text-gray-400">Žádné pobočky</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add modal -->
    <div v-if="addOpen" class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div class="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-6 flex flex-col gap-4">
        <h2 class="text-lg font-bold">Přidat pobočku</h2>
        <input
          v-model="addName"
          type="text"
          placeholder="Název pobočky"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                 focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
        />
        <p v-if="addError" class="text-red-600 text-sm">{{ addError }}</p>
        <div class="flex gap-3">
          <button
            @click="addOpen = false"
            class="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-sm transition"
          >
            Zrušit
          </button>
          <button
            @click="doAdd"
            :disabled="addName.trim() === '' || addLoading"
            class="flex-1 py-3 bg-[#111111] hover:bg-gray-800 text-white rounded-xl
                   font-bold text-sm transition disabled:opacity-50"
          >
            {{ addLoading ? 'Ukládám…' : 'Přidat' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Edit modal -->
    <div v-if="editOpen" class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div class="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-6 flex flex-col gap-4">
        <h2 class="text-lg font-bold">Upravit pobočku</h2>
        <input
          v-model="editName"
          type="text"
          placeholder="Název pobočky"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                 focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
        />
        <p v-if="editError" class="text-red-600 text-sm">{{ editError }}</p>
        <div class="flex gap-3">
          <button
            @click="editOpen = false"
            class="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-sm transition"
          >
            Zrušit
          </button>
          <button
            @click="doEdit"
            :disabled="editName.trim() === '' || editLoading"
            class="flex-1 py-3 bg-[#111111] hover:bg-gray-800 text-white rounded-xl
                   font-bold text-sm transition disabled:opacity-50"
          >
            {{ editLoading ? 'Ukládám…' : 'Uložit' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Delete confirm -->
    <div v-if="deleteOpen" class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div class="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-6 flex flex-col gap-4">
        <h2 class="text-lg font-bold">Smazat pobočku</h2>
        <p class="text-sm text-gray-600">
          Opravdu smazat pobočku <strong>{{ deleteRow?.name }}</strong>?
          Akce je nevratná.
        </p>
        <p v-if="deleteError" class="text-red-600 text-sm">{{ deleteError }}</p>
        <div class="flex gap-3">
          <button
            @click="deleteOpen = false"
            class="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-sm transition"
          >
            Zrušit
          </button>
          <button
            @click="doDelete"
            :disabled="deleteLoading"
            class="flex-1 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl
                   font-bold text-sm transition disabled:opacity-50"
          >
            {{ deleteLoading ? 'Mažu…' : 'Smazat' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
