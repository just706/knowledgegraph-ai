<template>
  <div class="profile-view">
    <van-nav-bar title="我的" />

    <div class="user-card">
      <van-icon name="manager-o" size="48" />
      <div class="info">
        <div class="name">{{ auth.user?.display_name || auth.user?.email || '游客' }}</div>
        <div class="email">{{ auth.user?.email || '未登录' }}</div>
        <van-tag v-if="auth.user?.role === 'admin'" type="danger">管理员</van-tag>
      </div>
    </div>

    <van-cell-group inset class="menu">
      <van-cell title="学习中心" icon="chart-trending-o" is-link to="/study" />
      <van-cell title="API 设置" icon="setting-o" is-link to="/settings" />
      <van-cell v-if="auth.user?.role === 'admin'" title="后台管理" icon="shield-o" is-link to="/admin" />
      <van-cell :title="auth.isLoggedIn ? '切换 / 登录我的账号' : '登录我的账号'" icon="exchange" is-link to="/login" />
      <van-cell v-if="auth.isLoggedIn" title="退出登录" icon="cross" @click="logout" />
    </van-cell-group>

    <!-- 原生 HTML 兜底：即使 vant 组件未加载也能看到状态与入口 -->
    <div class="native-panel">
      <div class="native-row">
        <span>当前状态：</span>
        <strong>{{ auth.isLoggedIn ? (auth.user?.email === '1234567@qq.com' ? '体验账户' : '已登录') : '游客模式' }}</strong>
      </div>
      <button v-if="!auth.isLoggedIn" class="native-btn" @click="$router.push('/login')">登录我的账号</button>
      <button v-else class="native-btn plain" @click="logout">退出登录</button>
      <p class="native-tip">登录入口已放到个人中心。如需使用自己的资料，请登录个人账号。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { showConfirmDialog, showToast } from 'vant'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()

async function logout() {
  await showConfirmDialog({ title: '退出登录', message: '确定要退出吗？' })
  auth.logout()
  showToast('已退出，当前为游客模式')
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

.native-panel {
  margin: 16px 20px;
  padding: 16px;
  background: var(--kg-card, #fff);
  border-radius: 12px;
  border: 1px solid var(--kg-border, #ebedf0);

  .native-row {
    font-size: 14px;
    color: var(--kg-text-primary, #323233);
    margin-bottom: 12px;
  }

  .native-btn {
    width: 100%;
    background: var(--kg-primary, #1989fa);
    color: #fff;
    border: none;
    border-radius: 999px;
    padding: 12px 0;
    font-size: 15px;
    margin-bottom: 10px;

    &.plain {
      background: #fff;
      color: var(--kg-primary, #1989fa);
      border: 1px solid var(--kg-primary, #1989fa);
    }
  }

  .native-tip {
    font-size: 12px;
    color: var(--kg-text-secondary, #969799);
    line-height: 1.5;
    margin: 0;
  }
}
</style>

