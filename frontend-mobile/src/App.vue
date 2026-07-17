<template>
  <div class="app-wrapper">
    <router-view />
  </div>
  <!-- 调试信息：帮助手机端远程定位当前路由与登录状态 -->
  <div v-if="showDebug" class="debug-bar" @click="showDebug = false">
    <div>route: {{ route.path }} | name: {{ String(route.name) }}</div>
    <div>logged: {{ auth.isLoggedIn }} | user: {{ auth.user?.email || '-' }}</div>
    <div>mounted: {{ mountedAt }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const showDebug = ref(true)
const mountedAt = ref('')

onMounted(() => {
  mountedAt.value = new Date().toLocaleTimeString()
  // 启动时尝试静默以体验账户登录，但不再强制跳转；各页面自己按需处理未登录态。
  auth
    .ensureSession()
    .then(() => {
      // 如果当前正好在登录/注册页且已登录，回到首页
      if ((route.name === 'login' || route.name === 'register') && auth.isLoggedIn) {
        router.replace({ name: 'chat' })
      }
    })
    .catch(() => {
      // 体验登录失败不阻塞，页面内会显示“点击体验”入口
    })
})
</script>

<style scoped>
.app-wrapper {
  min-height: 100vh;
}
.debug-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 70px;
  z-index: 9998;
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  font-size: 11px;
  line-height: 1.5;
  padding: 8px 12px;
  white-space: pre-wrap;
  word-break: break-all;
  pointer-events: auto;
}
</style>
