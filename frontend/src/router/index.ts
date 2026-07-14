import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

// 核心页面（AI 宪法第六章）：首页、知识库、AI问答、知识图谱、思维导图、错题本
const routes: RouteRecordRaw[] = [
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

export default router
