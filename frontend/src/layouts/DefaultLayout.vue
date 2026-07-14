<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)

const menus = [
  { path: '/', title: '首页' },
  { path: '/knowledge', title: '知识库' },
  { path: '/chat', title: 'AI 问答' },
  { path: '/graph', title: '知识图谱' },
  { path: '/mindmap', title: '思维导图' },
  { path: '/mistakes', title: '错题本' },
]
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
      <el-header class="layout__header">{{ route.meta.title || '知识学习助手' }}</el-header>
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
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  font-weight: 600;
}
.layout__main {
  padding: 20px;
}
</style>
