<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getHealth, type HealthCheck } from '@/api/health'

const health = ref<HealthCheck | null>(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    health.value = await getHealth()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="home">
    <h2>欢迎使用 KnowledgeGraph AI 智能学习助手</h2>
    <p class="home__desc">从“拥有资料”到“真正理解和掌握知识”。</p>
    <el-card v-loading="loading" class="home__card">
      <template #header>后端连接状态</template>
      <el-tag v-if="health" type="success">已连接：{{ health.app_name }} v{{ health.version }}</el-tag>
      <el-tag v-else type="info">等待连接…</el-tag>
    </el-card>
  </div>
</template>

<style scoped>
.home__desc {
  color: var(--color-text-secondary);
}
</style>
