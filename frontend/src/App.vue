<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const isOnline = ref(navigator.onLine)

function handleOnline() { isOnline.value = true }
function handleOffline() { isOnline.value = false }

onMounted(() => {
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
})

onUnmounted(() => {
  window.removeEventListener('online', handleOnline)
  window.removeEventListener('offline', handleOffline)
})
</script>

<template>
  <div
    v-if="!isOnline"
    class="fixed top-0 inset-x-0 z-50 bg-red-600 text-white text-center py-2 text-sm font-semibold"
  >
    Offline — nelze zpracovat kartičky
  </div>
  <RouterView />
</template>
