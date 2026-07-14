import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/store/auth'

// 核心页面（AI 宪法第六章）：首页、知识库、AI问答、知识图谱、思维导图、错题本
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/LoginPage.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/pages/RegisterPage.vue'),
    meta: { title: '注册', public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('@/pages/HomePage.vue'), meta: { title: '首页' } },
      { path: 'knowledge', name: 'knowledge', component: () => import('@/pages/KnowledgePage.vue'), meta: { title: '知识库' } },
      { path: 'chat', name: 'chat', component: () => import('@/pages/ChatPage.vue'), meta: { title: 'AI 问答' } },
      { path: 'graph', name: 'graph', component: () => import('@/pages/GraphPage.vue'), meta: { title: '知识图谱' } },
      { path: 'mindmap', name: 'mindmap', component: () => import('@/pages/MindMapPage.vue'), meta: { title: '思维导图' } },
      { path: 'mistakes', name: 'mistakes', component: () => import('@/pages/MistakePage.vue'), meta: { title: '错题本' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：未登录访问受保护页面 → 跳转登录（AI 宪法第五章：用户数据权限控制）
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if ((to.name === 'login' || to.name === 'register') && auth.isLoggedIn) {
    return { name: 'home' }
  }
  return true
})

export default router
