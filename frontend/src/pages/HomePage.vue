<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getStatsOverview, type StatsOverview } from '@/api/stats'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const auth = useAuthStore()
const stats = ref<StatsOverview | null>(null)
const loading = ref(false)

// 问候语
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})
const userName = computed(() => auth.user?.email?.split('@')[0] || '同学')

// 今日学习目标：由后端基于用户真实学习记录推导（薄弱点优先），不再写死
const todayGoal = computed(() => stats.value?.today_goal || '上传资料或完成练习后，这里会生成你的专属目标')

// 知识掌握度：来自后端基于用户真实练习/错题记录推导的 knowledge_mastery
const masteryList = computed(() => {
  const s = stats.value
  if (!s || !s.knowledge_mastery) return []
  return s.knowledge_mastery.map((m) => ({
    name: m.name,
    value: m.value,
    total: m.total,
    correct: m.correct,
  }))
})

// 最近学习（资料）
const recentDocs = computed(() =>
  (stats.value?.recent_documents || []).slice(0, 3).map((d) => ({
    title: d.title,
    time: d.created_at?.slice(0, 10) || '',
  })),
)

// AI 建议
const aiSuggestion = computed(() => stats.value?.ai_suggestion || '先从知识库上传资料，开启你的学习之旅。')

onMounted(async () => {
  loading.value = true
  try {
    stats.value = await getStatsOverview()
  } finally {
    loading.value = false
  }
})

function go(path: string) {
  router.push(path)
}
</script>

<template>
  <div class="cockpit" v-loading="loading">
    <!-- 问候 + 今日目标 -->
    <el-card class="hero" :body-style="{ padding: '24px 28px' }">
      <div class="hero__left">
        <h1 class="hero__hi">{{ greeting }}，{{ userName }} 👋</h1>
        <div class="hero__goal">
          <span class="hero__goal-label">今日学习目标</span>
          <span class="hero__goal-text">{{ todayGoal }}</span>
        </div>
      </div>
      <div class="hero__stats">
        <div class="hero__stat" @click="go('/knowledge')">
          <div class="hero__stat-num" style="color: #409eff">{{ stats?.document_count ?? 0 }}</div>
          <div class="hero__stat-label">学习资料</div>
        </div>
        <div class="hero__stat" @click="go('/graph')">
          <div class="hero__stat-num" style="color: #67c23a">{{ stats?.entity_count ?? 0 }}</div>
          <div class="hero__stat-label">知识实体</div>
        </div>
        <div class="hero__stat" @click="go('/quiz')">
          <div class="hero__stat-num" style="color: #e6a23c">{{ stats?.quiz_total ?? 0 }}</div>
          <div class="hero__stat-label">练习题目</div>
        </div>
        <div class="hero__stat" @click="go('/mistakes')">
          <div class="hero__stat-num" style="color: #f56c6c">{{ stats?.mistake_total ?? 0 }}</div>
          <div class="hero__stat-label">错题总数</div>
        </div>
      </div>
    </el-card>

    <div class="cockpit__grid">
      <!-- 知识掌握情况 -->
      <el-card class="panel">
        <template #header>知识掌握情况</template>
        <div class="mastery">
          <div v-for="m in masteryList" :key="m.name" class="mastery__row">
            <span class="mastery__name">{{ m.name }}</span>
            <div class="mastery__track">
              <div class="mastery__fill" :style="{ width: m.value + '%' }" />
            </div>
            <span class="mastery__pct">{{ m.value }}%</span>
            <span class="mastery__meta">{{ m.correct }}/{{ m.total }}</span>
          </div>
          <div v-if="!masteryList.length" class="empty">
            还没有学习记录，做完练习或整理错题后，这里会显示你的知识点掌握情况
          </div>
        </div>
      </el-card>

      <!-- 最近学习 -->
      <el-card class="panel">
        <template #header>最近学习</template>
        <div v-if="recentDocs.length" class="recent">
          <div v-for="(d, i) in recentDocs" :key="i" class="recent__item" @click="go('/knowledge')">
            <span class="recent__icon">📘</span>
            <div class="recent__body">
              <div class="recent__title">{{ d.title }}</div>
              <div class="recent__time">{{ d.time }}</div>
            </div>
          </div>
        </div>
        <div v-else class="empty">还没有学习记录，去上传资料吧</div>
      </el-card>

      <!-- AI 建议 -->
      <el-card class="panel panel--wide">
        <template #header>
          <span>AI 建议</span>
          <el-tag size="small" type="success" effect="plain" style="margin-left: 8px">智能</el-tag>
        </template>
        <div class="advice">
          <div class="advice__block">
            <div class="advice__title">你的薄弱知识</div>
            <div class="advice__content">
              {{
                (stats?.mistake_subject_dist || [])[0]?.name
                  ? '「' + (stats?.mistake_subject_dist || [])[0].name + '」相关概念'
                  : '暂无明显薄弱点，保持节奏 👍'
              }}
            </div>
          </div>
          <el-divider />
          <div class="advice__block">
            <div class="advice__title">推荐</div>
            <div class="advice__content">{{ aiSuggestion }}</div>
          </div>
          <el-button class="advice__btn" type="primary" plain @click="go('/quiz')">
            开始智能练习
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.cockpit {
  max-width: 1100px;
}
.hero {
  margin-bottom: 16px;
  background: linear-gradient(135deg, #f5f8ff 0%, #ffffff 60%);
  border: none;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.08);
}
.hero__hi {
  margin: 0 0 10px;
  font-size: 24px;
}
.hero__goal {
  display: flex;
  align-items: center;
  gap: 10px;
}
.hero__goal-label {
  font-size: 13px;
  color: #fff;
  background: var(--el-color-primary);
  border-radius: 12px;
  padding: 2px 10px;
}
.hero__goal-text {
  font-size: 15px;
  font-weight: 600;
}
.hero__stats {
  display: flex;
  gap: 28px;
  margin-top: 20px;
}
.hero__stat {
  text-align: center;
  cursor: pointer;
  flex: 1;
}
.hero__stat-num {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}
.hero__stat-label {
  margin-top: 6px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.cockpit__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.panel--wide {
  grid-column: 1 / -1;
}
.mastery__row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.mastery__name {
  width: 70px;
  font-size: 14px;
  text-align: right;
}
.mastery__track {
  flex: 1;
  height: 12px;
  background: #f0f2f5;
  border-radius: 6px;
  overflow: hidden;
}
.mastery__fill {
  height: 100%;
  border-radius: 6px;
  background: linear-gradient(90deg, #409eff, #67c23a);
  transition: width 0.5s;
}
.mastery__pct {
  width: 44px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.mastery__meta {
  width: 44px;
  font-size: 12px;
  color: var(--color-text-secondary);
  text-align: right;
}
.recent__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.recent__item:hover {
  background: #f5f8ff;
}
.recent__icon {
  font-size: 22px;
}
.recent__title {
  font-size: 14px;
  font-weight: 600;
}
.recent__time {
  font-size: 12px;
  color: var(--color-text-secondary);
}
.advice__block {
  margin-bottom: 6px;
}
.advice__title {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}
.advice__content {
  font-size: 15px;
  line-height: 1.6;
}
.advice__btn {
  margin-top: 12px;
}
.empty {
  color: var(--color-text-secondary);
  text-align: center;
  padding: 30px 0;
}
</style>
