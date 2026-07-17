<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getDashboard,
  listUsers,
  toggleUserActive,
  setUserRole,
  type AdminDashboard,
  type AdminUserSummary,
} from '@/api/admin'

// ---- 状态 ----
const loading = ref(false)
const dashboard = ref<AdminDashboard | null>(null)
const users = ref<AdminUserSummary[]>([])
const userLoading = ref(false)

// 筛选
const searchQuery = ref('')
const roleFilter = ref('')
const activeOnly = ref(false)

// ---- 生命周期 ----
onMounted(async () => {
  await Promise.all([fetchDashboard(), fetchUsers()])
})

async function fetchDashboard() {
  loading.value = true
  try {
    dashboard.value = await getDashboard()
  } finally {
    loading.value = false
  }
}

async function fetchUsers() {
  userLoading.value = true
  try {
    users.value = await listUsers({
      q: searchQuery.value || undefined,
      role: roleFilter.value || undefined,
      active_only: activeOnly.value || undefined,
    })
  } finally {
    userLoading.value = false
  }
}

// ---- 操作 ----
async function handleToggleActive(user: AdminUserSummary) {
  const action = user.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${action}用户 ${user.email} 吗？`, `${action}用户`, {
      type: 'warning',
    })
    const updated = await toggleUserActive(user.id, !user.is_active)
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx >= 0) users.value[idx] = updated
    ElMessage.success(`${action}成功`)
    fetchDashboard() // 刷新统计
  } catch {
    // 用户取消
  }
}

async function handleSetRole(user: AdminUserSummary, newRole: string) {
  try {
    const roleName = newRole === 'admin' ? '管理员' : '普通用户'
    await ElMessageBox.confirm(
      `确定将 ${user.email} 的角色设为「${roleName}」吗？`,
      '修改角色',
      { type: 'warning' },
    )
    const updated = await setUserRole(user.id, newRole)
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx >= 0) users.value[idx] = updated
    ElMessage.success('角色修改成功')
    fetchDashboard()
  } catch {
    // 用户取消
  }
}

// ---- 统计卡片 ----
const statCards = computed(() => {
  if (!dashboard.value) return []
  const s = dashboard.value.stats
  return [
    { label: '总用户', value: s.total_users, color: '#409EFF' },
    { label: '活跃用户', value: s.active_users, color: '#67C23A' },
    { label: '管理员', value: s.admin_users, color: '#E6A23C' },
    { label: '文档数', value: s.total_documents, color: '#909399' },
    { label: '切片数', value: s.total_chunks, color: '#909399' },
    { label: '对话数', value: s.total_chat_sessions, color: '#F56C6C' },
    { label: '消息数', value: s.total_chat_messages, color: '#F56C6C' },
    { label: '实体数', value: s.total_entities, color: '#409EFF' },
    { label: '关系数', value: s.total_relations, color: '#409EFF' },
    { label: '错题数', value: s.total_mistakes, color: '#E6A23C' },
    { label: '练习题', value: s.total_quizzes, color: '#67C23A' },
  ]
})
</script>

<template>
  <div class="admin-page">
    <h2 class="admin-page__title">后台管理</h2>

    <!-- 统计卡片 -->
    <el-row :gutter="16" v-loading="loading">
      <el-col
        v-for="card in statCards"
        :key="card.label"
        :xs="12"
        :sm="8"
        :md="6"
        :lg="4"
        style="margin-bottom: 16px"
      >
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-card__value" :style="{ color: card.color }">
              {{ card.value.toLocaleString() }}
            </div>
            <div class="stat-card__label">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 用户管理 -->
    <el-card style="margin-top: 24px">
      <template #header>
        <div class="user-header">
          <span>用户管理</span>
          <div class="user-header__filters">
            <el-input
              v-model="searchQuery"
              placeholder="搜索邮箱/名称"
              clearable
              style="width: 200px"
              @clear="fetchUsers"
              @keyup.enter="fetchUsers"
            />
            <el-select
              v-model="roleFilter"
              placeholder="角色"
              clearable
              style="width: 120px"
              @change="fetchUsers"
            >
              <el-option label="管理员" value="admin" />
              <el-option label="普通用户" value="user" />
            </el-select>
            <el-checkbox v-model="activeOnly" @change="fetchUsers">
              仅活跃
            </el-checkbox>
            <el-button type="primary" @click="fetchUsers">搜索</el-button>
          </div>
        </div>
      </template>

      <el-table :data="users" v-loading="userLoading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="display_name" label="昵称" min-width="120">
          <template #default="{ row }">
            {{ row.display_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'warning' : 'info'" size="small">
              {{ row.role === 'admin' ? '管理员' : '用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="170">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="文档" width="60" align="center">
          <template #default="{ row }">{{ row.document_count }}</template>
        </el-table-column>
        <el-table-column label="对话" width="60" align="center">
          <template #default="{ row }">{{ row.chat_session_count }}</template>
        </el-table-column>
        <el-table-column label="错题" width="60" align="center">
          <template #default="{ row }">{{ row.mistake_count }}</template>
        </el-table-column>
        <el-table-column label="练习" width="60" align="center">
          <template #default="{ row }">{{ row.quiz_count }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              :type="row.is_active ? 'warning' : 'success'"
              @click="handleToggleActive(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-dropdown
              trigger="click"
              @command="(role: string) => handleSetRole(row, role)"
            >
              <el-button size="small">
                角色 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    command="admin"
                    :disabled="row.role === 'admin'"
                  >
                    设为管理员
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="user"
                    :disabled="row.role === 'user'"
                  >
                    设为普通用户
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.admin-page {
  max-width: 1400px;
}
.admin-page__title {
  margin: 0 0 20px;
  font-size: 22px;
}
.stat-card {
  text-align: center;
  padding: 8px 0;
}
.stat-card__value {
  font-size: 28px;
  font-weight: bold;
}
.stat-card__label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
.user-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.user-header__filters {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
