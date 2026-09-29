import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'
import AccountsView from '@/views/admin/AccountsView.vue'

declare module 'vue-router' {
  interface RouteMeta { titleKey?: string; requiresAuth?: boolean; requiresAdmin?: boolean }
}

const routes: RouteRecordRaw[] = [
  { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { titleKey: 'routes.login' } },
  { path: '/forbidden', component: () => import('@/views/ForbiddenView.vue'), meta: { titleKey: 'routes.forbidden' } },
  {
    path: '/', component: () => import('@/layouts/AppLayout.vue'), meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { titleKey: 'routes.dashboard' } },
      { path: 'video/create', component: () => import('@/views/VideoCreateView.vue'), meta: { titleKey: 'routes.createVideo' } },
      { path: 'videos', component: () => import('@/views/VideosView.vue'), meta: { titleKey: 'routes.videos' } },
      { path: 'videos/:id', component: () => import('@/views/VideoDetailView.vue'), meta: { titleKey: 'routes.videoDetail' } },
      { path: 'publish', component: () => import('@/views/PublishView.vue'), meta: { titleKey: 'routes.publish' } },
      { path: 'publish/history', component: () => import('@/views/PublishHistoryView.vue'), meta: { titleKey: 'routes.publishHistory' } },
      { path: 'publish/:postId', component: () => import('@/views/PublishResultView.vue'), meta: { titleKey: 'routes.publishResult' } },
      { path: 'admin/users', component: () => import('@/views/admin/UsersView.vue'), meta: { titleKey: 'routes.users', requiresAdmin: true } },
      { path: 'admin/models', component: () => import('@/views/admin/ModelsView.vue'), meta: { titleKey: 'routes.models', requiresAdmin: true } },
      { path: 'admin/models/:id', component: () => import('@/views/admin/ModelEditorView.vue'), meta: { titleKey: 'routes.modelConfig', requiresAdmin: true } },
      { path: 'admin/platforms', component: () => import('@/views/admin/PlatformsView.vue'), meta: { titleKey: 'routes.platforms', requiresAdmin: true } },
      { path: 'admin/platforms/:id', component: () => import('@/views/admin/PlatformEditorView.vue'), meta: { titleKey: 'routes.platformConfig', requiresAdmin: true } },
      { path: 'admin/accounts', component: AccountsView, meta: { titleKey: 'routes.accounts', requiresAdmin: true } },
      { path: 'admin/logs', component: () => import('@/views/admin/LogsView.vue'), meta: { titleKey: 'routes.logs', requiresAdmin: true } },
    ],
  },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/NotFoundView.vue'), meta: { titleKey: 'routes.notFound' } },
]

const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) })
router.beforeEach(async (to) => {
  const auth = useAuthStore(pinia)
  if (auth.token && !auth.user && !auth.initialized) {
    try { await auth.fetchCurrentUser() } catch { auth.logout() }
  }
  if (to.path === '/login' && auth.isAuthenticated) return '/dashboard'
  if (to.matched.some((record) => record.meta.requiresAuth) && !auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.matched.some((record) => record.meta.requiresAdmin) && !auth.isAdmin) return '/forbidden'
  return true
})

export default router
