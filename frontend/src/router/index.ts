import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta { title?: string; requiresAuth?: boolean; requiresAdmin?: boolean }
}

const routes: RouteRecordRaw[] = [
  { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { title: '登录' } },
  { path: '/forbidden', component: () => import('@/views/ForbiddenView.vue'), meta: { title: '无权访问' } },
  {
    path: '/', component: () => import('@/layouts/AppLayout.vue'), meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '工作概览' } },
      { path: 'video/create', component: () => import('@/views/VideoCreateView.vue'), meta: { title: '制作视频' } },
      { path: 'videos', component: () => import('@/views/VideosView.vue'), meta: { title: '我的视频' } },
      { path: 'videos/:id', component: () => import('@/views/VideoDetailView.vue'), meta: { title: '视频详情' } },
      { path: 'publish', component: () => import('@/views/PublishView.vue'), meta: { title: '发布视频' } },
      { path: 'publish/history', component: () => import('@/views/PublishHistoryView.vue'), meta: { title: '发布记录' } },
      { path: 'admin/users', component: () => import('@/views/admin/UsersView.vue'), meta: { title: '用户管理', requiresAdmin: true } },
      { path: 'admin/models', component: () => import('@/views/admin/ModelsView.vue'), meta: { title: '视频模型', requiresAdmin: true } },
      { path: 'admin/models/:id', component: () => import('@/views/admin/ModelEditorView.vue'), meta: { title: '模型配置', requiresAdmin: true } },
      { path: 'admin/platforms', component: () => import('@/views/admin/PlatformsView.vue'), meta: { title: '发布平台', requiresAdmin: true } },
      { path: 'admin/platforms/:id', component: () => import('@/views/admin/PlatformEditorView.vue'), meta: { title: '平台配置', requiresAdmin: true } },
      { path: 'admin/accounts', component: () => import('@/views/admin/AccountsView.vue'), meta: { title: '发布账号', requiresAdmin: true } },
      { path: 'admin/logs', component: () => import('@/views/admin/LogsView.vue'), meta: { title: '操作日志', requiresAdmin: true } },
    ],
  },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/NotFoundView.vue'), meta: { title: '页面不存在' } },
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
  document.title = `${String(to.meta.title ?? '工作台')} · FrameFlow`
  return true
})

export default router
