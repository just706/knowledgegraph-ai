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

// 学习数据卡片
const dataCards = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    { label: '累计学习', value: s.study_hours, unit: '小时', color: '#409eff' },
    { label: '完成知识', value: s.entity_count, unit: '个', color: '#67c23a' },
    { label: '完成题目', value: s.quiz_total, unit: '道', color: '#e6a23c' },
    { label: '知识资料', value: s.document_count, unit: '份', color: '#f56c6c' },
  ]
})

// 能力雷达图（SVG 多边形）
const radar = computed(() => {
  const items = stats.value?.ability_radar || []
  const n = items.length || 1
  const cx = 130
  const cy = 130
  const R = 95
  const max = 100
  const point = (i: number, value: number) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2
    const r = (Math.min(value, max) / max) * R
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)]
  }
  const dataPts = items.map((it, i) => point(i, it.count))
  const polygon = dataPts.map((p) => p.join(',')).join(' ')
  const axes = items.map((_, i) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2
    return [cx + R * Math.cos(angle), cy + R * Math.sin(angle)]
  })
  return { cx, cy, R, n, items, dataPts, polygon, axes }
})

const aiSuggestion = computed(
  () => stats.value?.ai_suggestion || '继续学习并积累练习，系统会给出更精准的建议。',
)
</script>

<template>
  <div class="center" v-loading="loading">
    <div class="center__head">
      <h2>学习中心</h2>
      <p class="center__sub">记录你的成长轨迹，看清能力结构，找到下一步发力点。</p>
    </div>

    <!-- 学习数据 -->
    <div class="center__cards">
      <div v-for="c in dataCards" :key="c.label" class="data-card">
        <div class="data-card__value" :style="{ color: c.color }">
          {{ c.value }}<span class="data-card__unit">{{ c.unit }}</span>
        </div>
        <div class="data-card__label">{{ c.label }}</div>
      </div>
    </div>

    <div class="center__grid">
      <!-- 能力雷达图 -->
      <el-card class="panel">
        <template #header>能力雷达图</template>
        <div class="radar">
          <svg width="260" height="260" viewBox="0 0 260 260">
            <!-- 网格圈 -->
            <polygon
              v-for="ring in [0.25, 0.5, 0.75, 1]"
              :key="ring"
              :points="
                radar.axes
                  .map((p) => {
                    const cx2 = 130,
                      cy2 = 130
                    return `${cx2 + (p[0] - cx2) * ring},${cy2 + (p[1] - cy2) * ring}`
                  })
                  .join(' ')
              "
              fill="none"
              stroke="#ebeef5"
              stroke-width="1"
            />
            <!-- 轴线 -->
            <line
              v-for="(p, i) in radar.axes"
              :key="'ax' + i"
              x1="130"
              y1="130"
              :x2="p[0]"
              :y2="p[1]"
              stroke="#ebeef5"
            />
            <!-- 数据多边形 -->
            <polygon :points="radar.polygon" fill="rgba(64,158,255,0.18)" stroke="#409eff" stroke-width="2" />
            <circle v-for="(p, i) in radar.dataPts" :key="'pt' + i" :cx="p[0]" :cy="p[1]" r="3" fill="#409eff" />
            <!-- 维度标签 -->
            <text
              v-for="(it, i) in radar.items"
              :key="'lb' + i"
              :x="radar.axes[i][0] > 130 ? radar.axes[i][0] + 6 : radar.axes[i][0] - 6"
              :y="radar.axes[i][1] + 4"
              :text-anchor="radar.axes[i][0] > 130 ? 'start' : radar.axes[i][0] < 130 ? 'end' : 'middle'"
              font-size="12"
              fill="#606266"
            >
              {{ it.name }} {{ it.count }}
            </text>
          </svg>
        </div>
      </el-card>

      <!-- 学习建议 -->
      <el-card class="panel">
        <template #header>学习建议</template>
        <div class="advice">
          <div class="advice__icon">💡</div>
          <p class="advice__text">{{ aiSuggestion }}</p>
          <el-button type="primary" plain @click="router.push('/quiz')">去针对性练习</el-button>
        </div>
        <el-divider />
        <div class="advice__sub">
          <div class="advice__sub-title">能力维度</div>
          <div v-for="it in radar.items" :key="it.name" class="advice__sub-row">
            <span>{{ it.name }}</span>
            <el-progress :percentage="it.count" :stroke-width="10" style="flex: 1; margin-left: 12px" />
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.center__head h2 {
  margin: 0;
}
.center__sub {
  color: var(--color-text-secondary);
  margin: 6px 0 20px;
}
.center__cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.data-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.04);
}
.data-card__value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}
.data-card__unit {
  font-size: 14px;
  font-weight: 400;
  margin-left: 4px;
  color: var(--color-text-secondary);
}
.data-card__label {
  margin-top: 8px;
  color: var(--color-text-secondary);
  font-size: 14px;
}
.center__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.radar {
  display: flex;
  justify-content: center;
}
.advice {
  text-align: center;
}
.advice__icon {
  font-size: 32px;
}
.advice__text {
  font-size: 15px;
  line-height: 1.7;
  margin: 12px 0;
}
.advice__sub-title {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
}
.advice__sub-row {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
}
</style>
