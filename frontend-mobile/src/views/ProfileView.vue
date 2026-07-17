<template>
  <div class="profile-view">
    <van-nav-bar title="我的" />

    <div class="user-card">
      <van-icon name="manager-o" size="48" />
      <div class="info">
        <div class="name">{{ auth.user?.display_name || auth.user?.email }}</div>
        <div class="email">{{ auth.user?.email }}</div>
        <van-tag v-if="auth.user?.role === 'admin'" type="danger">管理员</van-tag>
      </div>
    </div>

    <van-cell-group inset class="menu">
      <van-cell title="API 设置" icon="setting-o" is-link to="/settings" />
      <van-cell v-if="auth.user?.role === 'admin'" title="后台管理" icon="shield-o" is-link to="/admin" />
      <van-cell title="退出登录" icon="cross" @click="logout" />
    </van-cell-group>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const auth = useAuthStore()

async function logout() {
  await showConfirmDialog({ title: '退出登录', message: '确定要退出吗？' })
  auth.logout()
  showToast('已退出')
  router.replace('/login')
}
</script>

<style scoped lang="scss">
.profile-view {
  min-height: calc(100vh - 50px);
}

.user-card {
  display: flex;
  align-items: center;
  padding: 32px 20px;
  background: linear-gradient(135deg, #1989fa, #5cadff);
  color: #fff;
}

.info {
  margin-left: 16px;

  .name { font-size: 18px; font-weight: 600; }
  .email { font-size: 13px; opacity: 0.8; margin: 4px 0; }
}

.menu {
  margin-top: 16px;
}
</style>
