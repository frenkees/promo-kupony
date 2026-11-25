<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const loginValue = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(loginValue.value, password.value)
    // Router guard zvládne must_change_password automaticky;
    // sem se dostanem jen pokud to není potřeba
    router.push(auth.role === 'operator' ? '/scan' : '/admin')
  } catch (e) {
    const detail = e.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : 'Přihlášení selhalo'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-[#111111] flex items-center justify-center p-4">
    <div class="w-full max-w-sm bg-white rounded-2xl shadow-xl p-8">
      <h1 class="text-2xl font-bold text-center mb-1">Promo Kartičky</h1>
      <p class="text-gray-400 text-center text-sm mb-6">Systém správy kuponů</p>

      <form @submit.prevent="submit" class="space-y-4">
        <input
          v-model="loginValue"
          type="text"
          placeholder="Login"
          autocomplete="username"
          required
          class="w-full border border-gray-300 rounded-lg px-4 py-3 text-lg
                 focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
        />
        <input
          v-model="password"
          type="password"
          placeholder="Heslo"
          autocomplete="current-password"
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
          {{ loading ? 'Přihlašuji…' : 'Přihlásit se' }}
        </button>
      </form>
    </div>
  </div>
</template>
