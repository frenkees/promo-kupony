<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const router = useRouter()
const auth = useAuthStore()

const oldPassword = ref('')
const newPassword = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await api.post('/auth/change-password', {
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    await auth.fetchMe()
    router.push(auth.role === 'operator' ? '/scan' : '/admin')
  } catch (e) {
    const detail = e.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : 'Změna hesla selhala'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-[#111111] flex items-center justify-center p-4">
    <div class="w-full max-w-sm bg-white rounded-2xl shadow-xl p-8">
      <h1 class="text-xl font-bold text-center mb-1">Změna hesla</h1>
      <p class="text-gray-500 text-sm text-center mb-6">
        Pro pokračování musíte nastavit nové heslo.
      </p>

      <form @submit.prevent="submit" class="space-y-4">
        <input
          v-model="oldPassword"
          type="password"
          placeholder="Současné heslo"
          autocomplete="current-password"
          required
          class="w-full border border-gray-300 rounded-lg px-4 py-3 text-lg
                 focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
        />
        <input
          v-model="newPassword"
          type="password"
          placeholder="Nové heslo (min. 8 znaků)"
          autocomplete="new-password"
          minlength="8"
          required
          class="w-full border border-gray-300 rounded-lg px-4 py-3 text-lg
                 focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
        />

        <p v-if="error" class="text-red-600 text-sm text-center">{{ error }}</p>

        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-[#2DD4BF] hover:bg-yellow-400 text-[#111111] font-bold
                 text-xl py-4 rounded-xl transition disabled:opacity-60"
        >
          {{ loading ? 'Ukládám…' : 'Nastavit nové heslo' }}
        </button>
      </form>
    </div>
  </div>
</template>
