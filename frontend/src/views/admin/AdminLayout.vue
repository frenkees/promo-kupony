<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const allTabs = [
  { name: 'AdminOverview',    label: 'Přehled',    path: '/admin' },
  { name: 'AdminSuspicious',  label: 'Podezřelé',  path: '/admin/suspicious' },
  { name: 'AdminCard',        label: 'Kartička',   path: '/admin/card' },
  { name: 'AdminImport',      label: 'Import',     path: '/admin/import' },
  { name: 'AdminRestaurants', label: 'Restaurace', path: '/admin/restaurants', masterOnly: true },
  { name: 'AdminAccounts',    label: 'Účty',       path: '/admin/accounts',    masterOnly: true },
]

const tabs = computed(() =>
  allTabs.filter(t => !t.masterOnly || auth.role === 'master')
)

async function logout() {
  await auth.logout()
  router.push('/login')
}

function isActive(tab) {
  return route.name === tab.name
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-gray-50">

    <!-- Header -->
    <header class="flex items-center justify-between px-4 py-3 bg-[#111111] text-white shrink-0">
      <span class="font-semibold">Administrace</span>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-400">{{ auth.account?.login }}</span>
        <button
          @click="logout"
          class="text-xs text-gray-400 hover:text-white transition"
        >
          Odhlásit
        </button>
      </div>
    </header>

    <!-- Nav tabs -->
    <nav class="flex border-b border-gray-200 bg-white shrink-0">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.name"
        :to="tab.path"
        class="px-5 py-3 text-sm font-medium border-b-2 transition"
        :class="isActive(tab)
          ? 'border-[#2DD4BF] text-[#111111]'
          : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300'"
      >
        {{ tab.label }}
      </RouterLink>
    </nav>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto">
      <RouterView />
    </div>

  </div>
</template>
