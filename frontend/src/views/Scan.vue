<script setup>
import { ref, watch, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Html5Qrcode } from 'html5-qrcode'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const router = useRouter()
const auth = useAuthStore()

const code = ref('')
const status = ref(null)
const currentCode = ref('')
const lastIssue = ref(null)
const loading = ref(false)
const scannerOpen = ref(false)
const torchOn = ref(false)
const bypassOpen = ref(false)
const bypassReason = ref('')
const codeInput = ref(null)
const notice = ref(null)

let html5QrCode = null
let resetTimer = null
let noticeTimer = null

function showNotice(text) {
  notice.value = text
  clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => { notice.value = null }, 3000)
}

function explainStateChange(cs, context) {
  if (cs === 'K_UPLATNENI') {
    return context === 'issue'
      ? 'Karta už byla vydána dříve.'
      : 'Karta už byla vydána mezitím, bypass není potřeba.'
  }
  if (cs === 'VYRAZENA') return 'Karta byla mezitím vyřazena.'
  return 'Stav karty se mezitím změnil.'
}

// Prefix QR kódů — předán z Vite buildu (docker-compose build arg → ENV VITE_QR_PREFIX).
// Fallback 'PROMO' pro lokální `npm run build` bez nastavení proměnné.
const QR_PREFIX = import.meta.env.VITE_QR_PREFIX || 'PROMO'

const BYPASS_REASONS = [
  'Jiná pobočka zapomněla vydat',
  'Technický výpadek při vydání',
  'Zákazník má platnou kartičku, systém ji nezná',
  'Jiný důvod',
]

function formatPrague(iso) {
  return new Date(iso).toLocaleString('cs-CZ', { timeZone: 'Europe/Prague' })
}

watch(code, (val) => {
  if (val.length === 4) submitCode(val)
})

async function submitCode(val) {
  clearTimeout(noticeTimer)
  notice.value = null
  currentCode.value = val
  code.value = ''
  lastIssue.value = null
  status.value = 'loading'
  try {
    const { data } = await api.get(`/coupons/${val}`)
    status.value = data.state
    lastIssue.value = data.last_issue
  } catch (e) {
    status.value = 'NOT_FOUND'
  }
}

async function doIssue() {
  loading.value = true
  try {
    await api.post(`/coupons/${currentCode.value}/issue`)
    status.value = 'OK_VYDANO'
    scheduleReset()
  } catch (e) {
    // 409 = stav už nebyl VOLNA (race condition — někdo vydal dřív, nebo karta vyřazena)
    if (e.response?.status === 409) {
      const cs = e.response.data?.detail?.current_state
      showNotice(explainStateChange(cs, 'issue'))
      status.value = cs || 'NOT_FOUND'
    } else {
      status.value = 'NOT_FOUND'
    }
    loading.value = false
  }
}

async function doRedeem() {
  loading.value = true
  try {
    await api.post(`/coupons/${currentCode.value}/redeem`)
    status.value = 'OK_UPLATNENO'
    scheduleReset()
  } catch (e) {
    if (e.response?.status === 409 && e.response.data?.detail?.current_state === 'VOLNA') {
      status.value = 'NEVYDANO'
    } else {
      status.value = 'NOT_FOUND'
    }
    loading.value = false
  }
}

async function doBypass() {
  loading.value = true
  try {
    await api.post(`/coupons/${currentCode.value}/redeem-bypass`, { reason: bypassReason.value })
    bypassOpen.value = false
    bypassReason.value = ''
    status.value = 'OK_BYPASS'
    scheduleReset()
  } catch (e) {
    bypassOpen.value = false
    bypassReason.value = ''
    if (e.response?.status === 409) {
      const cs = e.response.data?.detail?.current_state
      showNotice(explainStateChange(cs, 'bypass'))
      status.value = cs || 'NOT_FOUND'
    } else {
      status.value = 'NOT_FOUND'
    }
    loading.value = false
  }
}

function scheduleReset() {
  loading.value = false
  clearTimeout(resetTimer)
  resetTimer = setTimeout(async () => {
    status.value = null
    currentCode.value = ''
    lastIssue.value = null
    await nextTick()
    codeInput.value?.focus()
  }, 2000)
}

async function openScanner() {
  scannerOpen.value = true
  await nextTick()
  html5QrCode = new Html5Qrcode('qr-reader')
  await html5QrCode.start(
    { facingMode: 'environment' },
    { fps: 10, qrbox: { width: 250, height: 250 } },
    onQrSuccess,
    () => {},
  )
}

function onQrSuccess(payload) {
  closeScanner()
  const prefix = `${QR_PREFIX}-`
  const extracted = payload.startsWith(prefix) ? payload.slice(prefix.length) : payload
  submitCode(extracted)
}

async function closeScanner() {
  if (html5QrCode) {
    await html5QrCode.stop().catch(() => {})
    html5QrCode = null
  }
  scannerOpen.value = false
  torchOn.value = false
}

async function toggleTorch() {
  torchOn.value = !torchOn.value
  await html5QrCode?.applyVideoConstraints({ advanced: [{ torch: torchOn.value }] })
}

async function logout() {
  await auth.logout()
  router.push('/login')
}

onUnmounted(() => {
  closeScanner()
  clearTimeout(resetTimer)
  clearTimeout(noticeTimer)
})
</script>

<template>
  <div class="h-screen flex flex-col bg-gray-50 overflow-hidden">

    <!-- Header -->
    <header class="flex items-center justify-between px-4 py-3 bg-[#111111] text-white shrink-0">
      <span class="font-semibold text-sm truncate">
        {{ auth.restaurantName ?? 'Promo Kartičky' }}
      </span>
      <button
        @click="logout"
        class="text-xs text-gray-400 hover:text-white transition ml-4 shrink-0"
      >
        Odhlásit
      </button>
    </header>

    <!-- Info banner (auto-dismiss po 3 s) — pro silent state-change při 409 -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="notice"
           class="shrink-0 bg-yellow-100 border-b border-yellow-300 px-4 py-2
                  text-sm text-yellow-900 text-center font-medium">
        {{ notice }}
      </div>
    </Transition>

    <!-- Input sekce -->
    <div class="flex flex-col items-center gap-3 px-6 pt-6 pb-4 shrink-0">
      <input
        ref="codeInput"
        v-model="code"
        type="tel"
        inputmode="numeric"
        pattern="[0-9]*"
        maxlength="4"
        placeholder="Zadejte 4 číslice"
        autofocus
        :disabled="loading || status === 'loading'"
        class="w-full max-w-xs text-center text-3xl font-mono tracking-[0.5em] border-2
               border-gray-300 rounded-xl px-4 py-4 focus:outline-none focus:border-[#2DD4BF]
               disabled:opacity-50 placeholder:text-lg placeholder:tracking-normal placeholder:font-sans"
      />
      <button
        @click="openScanner"
        :disabled="loading || status === 'loading' || scannerOpen"
        class="flex items-center gap-2 px-5 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg
               text-sm font-medium transition disabled:opacity-50"
      >
        <span>📷</span> Skenovat QR
      </button>
    </div>

    <!-- Status panel -->
    <div class="flex-1 flex flex-col items-center justify-center px-6 py-4">

      <!-- Idle -->
      <div v-if="status === null" class="text-gray-400 text-center text-sm">
        Zadejte kód karty nebo naskenujte QR kód
      </div>

      <!-- Loading -->
      <div v-else-if="status === 'loading'"
           class="w-full max-w-sm rounded-2xl bg-gray-200 p-8 flex flex-col items-center gap-3">
        <div class="w-10 h-10 border-4 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-gray-600 font-medium">Načítám…</p>
      </div>

      <!-- VOLNA — modrá -->
      <div v-else-if="status === 'VOLNA'"
           class="w-full max-w-sm rounded-2xl bg-blue-100 border border-blue-300 p-8 flex flex-col items-center gap-4">
        <p class="text-4xl font-black text-blue-800 tracking-widest">{{ currentCode }}</p>
        <p class="text-blue-700 font-semibold text-lg">NEVYDÁNO</p>
        <p class="text-blue-600 text-sm">Karta čeká na vydání zákazníkovi</p>
        <button
          @click="doIssue"
          :disabled="loading"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl
                 text-xl transition disabled:opacity-60"
        >
          {{ loading ? 'Vydávám…' : 'VYDAT' }}
        </button>
      </div>

      <!-- K_UPLATNENI — oranžová -->
      <div v-else-if="status === 'K_UPLATNENI'"
           class="w-full max-w-sm rounded-2xl bg-orange-100 border border-orange-300 p-8 flex flex-col items-center gap-4">
        <p class="text-4xl font-black text-orange-800 tracking-widest">{{ currentCode }}</p>
        <p class="text-orange-700 font-semibold text-lg">VYDÁNO</p>
        <p class="text-orange-600 text-sm">Karta byla vydána, lze uplatnit</p>
        <p v-if="lastIssue" class="text-orange-500 text-xs">
          Vydáno: {{ formatPrague(lastIssue) }}
        </p>
        <button
          @click="doRedeem"
          :disabled="loading"
          class="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-4 rounded-xl
                 text-xl transition disabled:opacity-60"
        >
          {{ loading ? 'Uplatňuji…' : 'UPLATNIT' }}
        </button>
      </div>

      <!-- VYRAZENA — červená -->
      <div v-else-if="status === 'VYRAZENA'"
           class="w-full max-w-sm rounded-2xl bg-red-100 border border-red-300 p-8 flex flex-col items-center gap-4">
        <p class="text-4xl font-black text-red-800 tracking-widest">{{ currentCode }}</p>
        <p class="text-red-700 font-semibold text-lg">NEPLATNÁ</p>
        <p class="text-red-600 text-sm">Karta byla vyřazena a nelze použít</p>
      </div>

      <!-- NOT_FOUND — červená -->
      <div v-else-if="status === 'NOT_FOUND'"
           class="w-full max-w-sm rounded-2xl bg-red-100 border border-red-300 p-8 flex flex-col items-center gap-4">
        <p class="text-4xl font-black text-red-800 tracking-widest">{{ currentCode }}</p>
        <p class="text-red-700 font-semibold text-lg">NEZNÁMÝ KÓD</p>
        <p class="text-red-600 text-sm">Karta nebyla nalezena v systému</p>
        <button
          @click="status = null; currentCode = ''"
          class="mt-2 px-6 py-2 bg-red-200 hover:bg-red-300 rounded-lg text-sm font-medium transition"
        >
          Zkusit znovu
        </button>
      </div>

      <!-- NEVYDANO — červená + bypass -->
      <div v-else-if="status === 'NEVYDANO'"
           class="w-full max-w-sm rounded-2xl bg-red-100 border border-red-300 p-8 flex flex-col items-center gap-4">
        <p class="text-4xl font-black text-red-800 tracking-widest">{{ currentCode }}</p>
        <p class="text-red-700 font-semibold text-lg">NEVYDÁNO</p>
        <p class="text-red-600 text-sm">Karta nebyla zákazníkovi vydána</p>
        <button
          @click="bypassOpen = true"
          class="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-4 rounded-xl
                 text-xl transition"
        >
          BYPASS (uplatnit bez vydání)
        </button>
      </div>

      <!-- OK_VYDANO — zelená -->
      <div v-else-if="status === 'OK_VYDANO'"
           class="w-full max-w-sm rounded-2xl bg-green-100 border border-green-400 p-8 flex flex-col items-center gap-3">
        <p class="text-5xl">✓</p>
        <p class="text-4xl font-black text-green-800 tracking-widest">{{ currentCode }}</p>
        <p class="text-green-700 font-bold text-xl">VYDÁNO ✓</p>
      </div>

      <!-- OK_UPLATNENO — zelená -->
      <div v-else-if="status === 'OK_UPLATNENO'"
           class="w-full max-w-sm rounded-2xl bg-green-100 border border-green-400 p-8 flex flex-col items-center gap-3">
        <p class="text-5xl">✓</p>
        <p class="text-4xl font-black text-green-800 tracking-widest">{{ currentCode }}</p>
        <p class="text-green-700 font-bold text-xl">UPLATNĚNO ✓</p>
      </div>

      <!-- OK_BYPASS — zelená -->
      <div v-else-if="status === 'OK_BYPASS'"
           class="w-full max-w-sm rounded-2xl bg-green-100 border border-green-400 p-8 flex flex-col items-center gap-3">
        <p class="text-5xl">✓</p>
        <p class="text-4xl font-black text-green-800 tracking-widest">{{ currentCode }}</p>
        <p class="text-green-700 font-bold text-xl">UPLATNĚNO ✓ (bypass)</p>
      </div>

    </div>

    <!-- QR Scanner overlay -->
    <div v-if="scannerOpen"
         class="fixed inset-0 z-40 bg-black flex flex-col">
      <div id="qr-reader" class="flex-1"></div>
      <div class="flex gap-4 justify-center p-5 shrink-0">
        <button
          @click="toggleTorch"
          class="px-6 py-3 rounded-xl font-semibold transition"
          :class="torchOn ? 'bg-yellow-400 text-black' : 'bg-gray-700 text-white'"
        >
          {{ torchOn ? '🔦 Svítilna ZAP' : '🔦 Svítilna' }}
        </button>
        <button
          @click="closeScanner"
          class="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl font-semibold transition"
        >
          Zavřít
        </button>
      </div>
    </div>

    <!-- Bypass modal -->
    <div v-if="bypassOpen"
         class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div class="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-6 flex flex-col gap-4">
        <h2 class="text-lg font-bold text-center">Bypass — uplatnění bez vydání</h2>
        <p class="text-sm text-gray-500 text-center">
          Karta <span class="font-mono font-bold text-gray-800">{{ currentCode }}</span>
          nebyla vydána. Vyberte důvod pro bypass.
        </p>
        <select
          v-model="bypassReason"
          class="w-full border border-gray-300 rounded-lg px-3 py-3 text-sm
                 focus:outline-none focus:ring-2 focus:ring-[#2DD4BF]"
        >
          <option value="">— Vyberte důvod —</option>
          <option v-for="r in BYPASS_REASONS" :key="r" :value="r">{{ r }}</option>
        </select>
        <div class="flex gap-3">
          <button
            @click="bypassOpen = false; bypassReason = ''"
            class="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-sm transition"
          >
            Zrušit
          </button>
          <button
            @click="doBypass"
            :disabled="bypassReason === '' || loading"
            class="flex-1 py-3 bg-[#2DD4BF] hover:bg-yellow-400 text-[#111111] rounded-xl
                   font-bold text-sm transition disabled:opacity-50"
          >
            {{ loading ? 'Ukládám…' : 'Potvrdit' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
