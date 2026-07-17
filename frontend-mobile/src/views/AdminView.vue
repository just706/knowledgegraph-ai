<template>
  <div class="admin-view">
    <van-nav-bar title="后台管理" left-text="返回" left-arrow @click-left="goBack" />

    <div v-if="dashboard" class="stats-grid">
      <div class="stat-card">
        <div class="num">{{ dashboard.total_users }}</div>
        <div class="label">用户总数</div>
      </div>
      <div class="stat-card">
        <div class="num">{{ dashboard.total_documents }}</div>
        <div class="label">资料总数</div>
      </div>
      <div class="stat-card">
        <div class="num">{{ dashboard.total_mistakes }}</div>
        <div class="label">错题总数</div>
      </div>
      <div class="stat-card">
        <div class="num">{{ dashboard.active_users }}</div>
        <div class="label">活跃用户</div>
      </div>
    </div>

    <van-cell-group inset title="用户管理" class="user-list">
      <van-cell v-for="u in users" :key="u.id" :title="u.email" :label="u.display_name || ''">
        <template #value>
          <van-tag :type="u.role === 'admin' ? 'danger' : 'default'">{{ u.role }}</van-tag>
        </template>
        <template #right-icon>
          <van-switch
            :model-value="u.is_active"
            size="20"
            @update:model-value="(v: boolean) => toggleActive(u, v)"
          />
        </template>
      </van-cell>
    </van-cell-group>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getDashboard, listUsers, updateUser, type AdminDashboard, type AdminUserSummary } from '@/api/admin'

const router = useRouter()
const dashboard = ref<AdminDashboard | null>(null)
const users = ref<AdminUserSummary[]>([])

async function load() {
  dashboard.value = await getDashboard()
  users.value = await listUsers({ limit: 50 })
}

async function toggleActive(u: AdminUserSummary, active: boolean) {
  await updateUser(u.id, { is_active: active })
  u.is_active = active
  showToast('已更新')
}

function goBack() {
  router.back()
}

onMounted(load)
</script>

<style scoped lang="scss">
.admin-view {
  min-height: calc(100vh - 50px);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 16px;
}

.stat-card {
  background: var(--kg-card);
  border-radius: 12px;
  padding: 16px;
  text-align: center;

  .num { font-size: 24px; font-weight: 700; color: var(--kg-primary); }
  .label { font-size: 12px; color: var(--kg-text-secondary); margin-top: 4px; }
}

.user-list {
  margin-top: 8px;
}
</style>
