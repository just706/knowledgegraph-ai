import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/TabBarLayout.vue'),
    children: [
      { path: '', redirect: '/chat' },
      { path: 'chat', name: 'chat', component: () => import('@/views/ChatView.vue'), meta: { title: 'AI助手' } },
      { path: 'knowledge', name: 'knowledge', component: () => import('@/views/KnowledgeView.vue'), meta: { title: '知识库' } },
      { path: 'quiz', name: 'quiz', component: () => import('@/views/QuizView.vue'), meta: { title: '练习' } },
      { path: 'mistakes', name: 'mistakes', component: () => import('@/views/MistakeView.vue'), meta: { title: '错题本' } },
      { path: 'map', name: 'map', component: () => import('@/views/MapView.vue'), meta: { title: '知识地图' } },
      { path: 'profile', name: 'profile', component: () => import('@/views/ProfileView.vue'), meta: { title: '我的' } },
      { path: 'settings', name: 'settings', component: () => import('@/views/SettingsView.vue'), meta: { title: 'API设置' } },
      { path: 'admin', name: 'admin', component: () => import('@/views/AdminView.vue'), meta: { title: '后台管理', admin: true } },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if ((to.name === 'login' || to.name === 'register') && auth.isLoggedIn) {
    return { name: 'chat' }
  }
  if (to.meta.admin && auth.user && auth.user.role !== 'admin') {
    return { name: 'chat' }
  }
  return true
})

export default router
