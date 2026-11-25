import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/change-password',
    name: 'ChangePassword',
    component: () => import('@/views/ChangePassword.vue'),
  },
  {
    path: '/scan',
    name: 'Scan',
    component: () => import('@/views/Scan.vue'),
    meta: { minRole: 'operator' },
  },
  {
    path: '/admin',
    component: () => import('@/views/admin/AdminLayout.vue'),
    meta: { minRole: 'manager' },
    children: [
      { path: '',           name: 'AdminOverview',   component: () => import('@/views/admin/Overview.vue') },
      { path: 'suspicious', name: 'AdminSuspicious', component: () => import('@/views/admin/Suspicious.vue') },
      { path: 'card',       name: 'AdminCard',       component: () => import('@/views/admin/CardHistory.vue') },
      { path: 'import',       name: 'AdminImport',       component: () => import('@/views/admin/Import.vue') },
      { path: 'restaurants',  name: 'AdminRestaurants',  component: () => import('@/views/admin/Restaurants.vue'), meta: { minRole: 'master' } },
      { path: 'accounts',     name: 'AdminAccounts',     component: () => import('@/views/admin/Accounts.vue'),    meta: { minRole: 'master' } },
    ],
  },
  { path: '/', redirect: '/login' },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function roleHome(role) {
  return role === 'operator' ? '/scan' : '/admin'
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()

  // Veřejné trasy (login) — vždy povol
  if (to.meta.public) return true

  // Nepřihlášen → login
  if (!auth.account) return '/login'

  // Vynucená změna hesla
  if (auth.mustChangePassword && to.name !== 'ChangePassword') {
    return '/change-password'
  }

  // Operátor se snaží na manažerskou sekci → přesměruj na scan
  if (to.meta.minRole === 'manager' && auth.role === 'operator') {
    return '/scan'
  }

  // Manager/operátor se snaží na master sekci → přesměruj na /admin
  if (to.meta.minRole === 'master' && auth.role !== 'master') {
    return '/admin'
  }

  return true
})

export { roleHome }
export default router
