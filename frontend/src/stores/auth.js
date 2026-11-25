import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const account = ref(null)
  const role = ref(null)
  const restaurantId = ref(null)
  const restaurantName = ref(null)
  const mustChangePassword = ref(false)
  const initDone = ref(false)

  async function fetchMe() {
    const { data } = await api.get('/auth/me')
    account.value = data
    role.value = data.role
    restaurantId.value = data.restaurant_id
    restaurantName.value = data.restaurant_name ?? null
    mustChangePassword.value = data.must_change_password
  }

  async function init() {
    if (initDone.value) return
    initDone.value = true
    try {
      await fetchMe()
    } catch {
      // není přihlášen — tiché selhání, account zůstane null
    }
  }

  async function login(loginValue, password) {
    const { data } = await api.post('/auth/login', { login: loginValue, password })
    role.value = data.role
    restaurantId.value = data.restaurant_id
    mustChangePassword.value = data.must_change_password
    account.value = { login: loginValue, role: data.role }
  }

  async function logout() {
    try {
      await api.post('/auth/logout')
    } finally {
      account.value = null
      role.value = null
      restaurantId.value = null
      restaurantName.value = null
      mustChangePassword.value = false
      initDone.value = false
    }
  }

  return {
    account,
    role,
    restaurantId,
    restaurantName,
    mustChangePassword,
    init,
    login,
    logout,
    fetchMe,
  }
})
