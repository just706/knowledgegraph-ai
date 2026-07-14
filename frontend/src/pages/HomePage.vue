<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getStatsOverview, type StatsOverview } from '@/api/stats'

const router = useRouter()
const stats = ref<StatsOverview | null>(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    stats.value = await getStatsOverview()
  } finally {
    loading.value = false
  }
})

// 概览卡片
const cards = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    { label: '学习资料', value: s.document_count, unit: '份', to: '/knowledge', color: '#409eff' },
    { label: '知识实体', value: s.entity_count, unit: '个', to: '/graph', color: '#67c23a' },
    { label: '知识关系', value: s.relation_count, unit: '条', to: '/graph', color: '#e6a23c' },
    { label: '错题总数', value: s.mistake_total, unit: '题', to: '/mistakes', color: '#f56c6c' },
  ]
})

// 掌握率环形图角度
const masteryDeg = computed(() => Math.round((stats.value?.mastery_rate ?? 0) * 3.6))

// 主题分布：取最大值做归一化
const subjectMax = computed(() =>
  Math.max(1, ...(stats.value?.mistake_subject_dist ?? []).map((i) => i.count)),
)
const labelMax = computed(() =>
  Math.max(1, ...(stats.value?.entity_label_dist ?? []).map((i) => i.count)),
)
const trendMax = computed(() =>
  Math.max(1, ...(stats.value?.mistake_trend_7d ?? []).map((i) => i.count)),
)

function fmtDay(d: string) {
  return d.slice(5) // MM-DD
}
</script>

<template>
  <div class="dash" v-loading="loading">
    <div class="dash__head">
      <h2>学习仪表盘</h2>
      <p class="dash__desc">从“拥有资料”到“真正理解和掌握知识”。</p>
    </div>

    <!-- 概览卡片 -->
    <div class="dash__cards">
      <div
        v-for="c in cards"
        :key="c.label"
        class="stat-card"
        @click="router.push(c.to)"
      >
        <div class="stat-card__value" :style="{ color: c.color }">
          {{ c.value }}<span class="stat-card__unit">{{ c.unit }}</span>
        </div>
        <div class="stat-card__label">{{ c.label }}</div>
      </div>
    </div>

    <div class="dash__grid">
      <!-- 掌握率 -->
      <el-card class="panel">
        <template #header>错题掌握率</template>
        <div class="mastery">
          <div
            class="mastery__ring"
            :style="{
              background: `conic-gradient(#67c23a ${masteryDeg}deg, #ebeef5 ${masteryDeg}deg)`,
            }"
          >
            <div class="mastery__hole">
              <div class="mastery__num">{{ stats?.mastery_rate ?? 0 }}%</div>
              <div class="mastery__sub">已掌握</div>
            </div>
          </div>
          <div class="mastery__legend">
            <div>已掌握：<b>{{ stats?.mistake_mastered ?? 0 }}</b> 题</div>
            <div>待巩固：<b>{{ (stats?.mistake_total ?? 0) - (stats?.mistake_mastered ?? 0) }}</b> 题</div>
          </div>
        </div>
      </el-card>

      <!-- 近 7 天错题趋势 -->
      <el-card class="panel">
        <template #header>近 7 天错题录入</template>
        <div class="trend">
          <div v-for="t in stats?.mistake_trend_7d ?? []" :key="t.date" class="trend__col">
            <div class="trend__bar-wrap">
              <div
                class="trend__bar"
                :style="{ height: `${(t.count / trendMax) * 100}%` }"
                :title="`${t.count} 题`"
              />
            </div>
            <div class="trend__count">{{ t.count }}</div>
            <div class="trend__day">{{ fmtDay(t.date) }}</div>
          </div>
        </div>
      </el-card>

      <!-- 错题主题分布 -->
      <el-card class="panel">
        <template #header>错题主题分布</template>
        <div v-if="(stats?.mistake_subject_dist?.length ?? 0) === 0" class="empty">暂无错题</div>
        <div v-else class="barlist">
          <div v-for="i in stats?.mistake_subject_dist ?? []" :key="i.name" class="barlist__row">
            <span class="barlist__name">{{ i.name }}</span>
            <div class="barlist__track">
              <div
                class="barlist__fill"
                :style="{ width: `${(i.count / subjectMax) * 100}%`, background: '#f56c6c' }"
              />
            </div>
            <span class="barlist__num">{{ i.count }}</span>
          </div>
        </div>
      </el-card>

      <!-- 实体类型分布 -->
      <el-card class="panel">
        <template #header>知识实体类型分布</template>
        <div v-if="(stats?.entity_label_dist?.length ?? 0) === 0" class="empty">暂无图谱数据</div>
        <div v-else class="barlist">
          <div v-for="i in stats?.entity_label_dist ?? []" :key="i.name" class="barlist__row">
            <span class="barlist__name">{{ i.name }}</span>
            <div class="barlist__track">
              <div
                class="barlist__fill"
                :style="{ width: `${(i.count / labelMax) * 100}%`, background: '#67c23a' }"
              />
            </div>
            <span class="barlist__num">{{ i.count }}</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.dash__head h2 {
  margin: 0;
}
.dash__desc {
  color: var(--color-text-secondary);
  margin: 6px 0 20px;
}
.dash__cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}
.stat-card__value {
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
}
.stat-card__unit {
  font-size: 14px;
  font-weight: 400;
  margin-left: 4px;
  color: var(--color-text-secondary);
}
.stat-card__label {
  margin-top: 8px;
  color: var(--color-text-secondary);
  font-size: 14px;
}
.dash__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.panel {
  min-height: 220px;
}
/* 掌握率环 */
.mastery {
  display: flex;
  align-items: center;
  gap: 28px;
}
.mastery__ring {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mastery__hole {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.mastery__num {
  font-size: 24px;
  font-weight: 700;
  color: #67c23a;
}
.mastery__sub {
  font-size: 12px;
  color: var(--color-text-secondary);
}
.mastery__legend {
  font-size: 14px;
  line-height: 2;
}
/* 趋势柱 */
.trend {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  height: 160px;
  gap: 8px;
}
.trend__col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.trend__bar-wrap {
  height: 110px;
  width: 60%;
  display: flex;
  align-items: flex-end;
}
.trend__bar {
  width: 100%;
  min-height: 2px;
  background: #409eff;
  border-radius: 4px 4px 0 0;
  transition: height 0.3s;
}
.trend__count {
  font-size: 12px;
  margin-top: 4px;
  color: var(--color-text-secondary);
}
.trend__day {
  font-size: 11px;
  color: var(--color-text-secondary);
}
/* 条形列表 */
.barlist__row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.barlist__name {
  width: 72px;
  font-size: 13px;
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.barlist__track {
  flex: 1;
  height: 14px;
  background: #f0f2f5;
  border-radius: 7px;
  overflow: hidden;
}
.barlist__fill {
  height: 100%;
  border-radius: 7px;
  transition: width 0.4s;
}
.barlist__num {
  width: 28px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.empty {
  color: var(--color-text-secondary);
  text-align: center;
  padding: 40px 0;
}
</style>
