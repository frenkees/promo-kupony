<script setup>
import { ref } from 'vue'
import api from '@/api'

const fileInput = ref(null)
const selectedFile = ref(null)
const result = ref(null)
const loading = ref(false)
const error = ref('')

function onFileChange(e) {
  selectedFile.value = e.target.files[0] ?? null
  result.value = null
  error.value = ''
}

async function upload() {
  if (!selectedFile.value) return
  loading.value = true
  result.value = null
  error.value = ''
  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    const { data } = await api.post('/coupons/import', fd)
    result.value = data
  } catch (e) {
    const detail = e.response?.data?.detail
    if (Array.isArray(detail)) {
      error.value = 'Neplatný formát souboru (chybí sloupec "code")'
    } else if (typeof detail === 'string') {
      error.value = detail
    } else {
      error.value = 'Import se nezdařil'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="p-6 max-w-xl mx-auto">

    <div class="bg-white rounded-xl border border-gray-200 p-6">
      <h2 class="text-base font-semibold text-gray-800 mb-1">Import kartiček z CSV</h2>
      <p class="text-sm text-gray-500 mb-5">
        Soubor musí mít sloupec <code class="bg-gray-100 px-1 rounded">code</code>.
        Existující kódy budou přeskočeny.
      </p>

      <div class="flex flex-col gap-4">
        <label
          class="flex items-center gap-3 border-2 border-dashed border-gray-300 rounded-xl px-5 py-4
                 cursor-pointer hover:border-[#2DD4BF] transition"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".csv"
            class="hidden"
            @change="onFileChange"
          />
          <span class="text-2xl">📄</span>
          <span class="text-sm text-gray-600">
            {{ selectedFile ? selectedFile.name : 'Klikněte pro výběr souboru (.csv)' }}
          </span>
        </label>

        <button
          @click="upload"
          :disabled="!selectedFile || loading"
          class="w-full py-3 bg-[#111111] hover:bg-gray-800 text-white font-bold
                 rounded-xl text-sm transition disabled:opacity-50"
        >
          {{ loading ? 'Nahrávám…' : 'Nahrát' }}
        </button>
      </div>

      <!-- Výsledek -->
      <div
        v-if="result"
        class="mt-5 flex items-center gap-3 bg-green-50 border border-green-300 rounded-xl px-5 py-4"
      >
        <span class="text-xl">✓</span>
        <div class="text-sm">
          <span class="font-semibold text-green-800">Import dokončen.</span>
          <span class="text-green-700 ml-2">
            Přidáno: <strong>{{ result.added }}</strong>,
            Přeskočeno: <strong>{{ result.skipped }}</strong>
          </span>
        </div>
      </div>

      <!-- Chyba -->
      <div
        v-if="error"
        class="mt-5 flex items-center gap-3 bg-red-50 border border-red-300 rounded-xl px-5 py-4"
      >
        <span class="text-xl">✗</span>
        <p class="text-sm text-red-700">{{ error }}</p>
      </div>
    </div>

  </div>
</template>
