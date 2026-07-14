<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const activeMenu = computed(() => route.path)

const menus = [
  { path: '/', title: '首页' },
  { path: '/knowledge', title: '知识库' },
  { path: '/chat', title: 'AI 问答' },
  { path: '/graph', title: '知识图谱' },
  { path: '/mindmap', title: '思维导图' },
  { path: '/mistakes', title: '错题本' },
]

onMounted(async () => {
  if (auth.isLoggedIn && !auth.user) {
    try {
      await auth.fetchUser()
    } catch {
      auth.logout()
    }
  }
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="200px" class="layout__aside">
      <div class="layout__logo">KnowledgeGraph AI</div>
      <el-menu :default-active="activeMenu" router class="layout__menu">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          {{ m.title }}
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="layout__header">
        <span>{{ route.meta.title || '知识学习助手' }}</span>
        <div v-if="auth.user" class="layout__user">
          <span class="layout__email">{{ auth.user.email }}</span>
          <el-button text type="primary" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="layout__main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100%;
}
.layout__aside {
  background: #001529;
  color: #fff;
}
.layout__logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: #fff;
}
.layout__menu {
  border-right: none;
  background: #001529;
}
.layout__menu :deep(.el-menu-item) {
  color: #c0c4cc;
}
.layout__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  font-weight: 600;
}
.layout__user {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: normal;
}
.layout__email {
  color: var(--color-text-secondary);
  font-size: 14px;
}
.layout__main {
  padding: 20px;
}
</style>
