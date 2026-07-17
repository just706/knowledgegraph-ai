<template>
  <div class="study-center">
    <van-nav-bar title="学习中心" />

    <div v-if="loading" class="loading-wrap">
      <van-loading type="spinner" color="#1989fa" />
    </div>

    <template v-else>
      <!-- 问候 + 今日目标 -->
      <div class="hero">
        <div class="greeting">{{ greeting }}，{{ nickname }}</div>
        <div v-if="data.today_goal" class="today-goal">
          <van-icon name="aim" />
          <span>今日目标：{{ data.today_goal }}</span>
        </div>
        <div class="study-hours">
          <van-icon name="clock-o" /> 累计学习 {{ data.study_hours.toFixed(1) }} 小时
        </div>
      </div>

      <!-- 概览卡片 -->
      <div class="overview-grid">
        <div class="ov-card" @click="go('knowledge')">
          <div class="ov-num">{{ data.document_count }}</div>
          <div class="ov-label">学习资料</div>
        </div>
        <div class="ov-card" @click="go('map')">
          <div class="ov-num">{{ data.entity_count }}</div>
          <div class="ov-label">知识点</div>
        </div>
        <div class="ov-card" @click="go('mistakes')">
          <div class="ov-num">{{ data.mistake_total }}</div>
          <div class="ov-label">错题</div>
        </div>
        <div class="ov-card" @click="go('quiz')">
          <div class="ov-num">{{ data.mastered_entity_count }}</div>
          <div class="ov-label">已掌握</div>
        </div>
      </div>

      <!-- 掌握率环形 -->
      <div class="card">
        <div class="card-title">整体掌握率</div>
        <div class="mastery-ring">
          <svg viewBox="0 0 120 120" class="ring">
            <circle cx="60" cy="60" r="52" class="ring-bg" />
            <circle
              cx="60" cy="60" r="52"
              class="ring-fg"
              :stroke-dasharray="circumference"
              :stroke-dashoffset="circumference * (1 - data.mastery_rate / 100)"
            />
          </svg>
          <div class="ring-text">
            <div class="ring-pct">{{ Math.round(data.mastery_rate) }}%</div>
            <div class="ring-sub">已掌握 {{ data.mistake_mastered }}/{{ data.mistake_total }}</div>
          </div>
        </div>
      </div>

      <!-- 知识点掌握度 -->
      <div class="card" v-if="data.knowledge_mastery.length">
        <div class="card-title">知识点掌握度</div>
        <div class="mastery-list">
          <div v-for="k in data.knowledge_mastery" :key="k.name" class="mastery-item">
            <div class="mi-head">
              <span class="mi-name">{{ k.name }}</span>
              <span class="mi-val">{{ k.value }}%</span>
            </div>
            <van-progress :percentage="k.value" :color="barColor(k.value)" :show-pivot="false" />
            <div class="mi-sub">答对 {{ k.correct }}/{{ k.total }}</div>
          </div>
        </div>
      </div>

      <!-- 能力雷达 -->
      <div class="card" v-if="data.ability_radar.length">
        <div class="card-title">能力维度</div>
        <div class="radar-wrap">
          <svg viewBox="0 0 200 200" class="radar">
            <polygon
              v-for="(ring, i) in radarRings"
              :key="'r' + i"
              :points="ring"
              class="radar-grid"
            />
            <line
              v-for="(axis, i) in radarAxes"
              :key="'a' + i"
              :x1="axis.x1" :y1="axis.y1" :x2="axis.x2" :y2="axis.y2"
              class="radar-line"
            />
            <polygon :points="radarPolygon" class="radar-area" />
            <text
              v-for="(label, i) in data.ability_radar"
              :key="'l' + i"
              :x="radarAxes[i].lx" :y="radarAxes[i].ly"
              class="radar-label"
            >{{ label.name }}</text>
          </svg>
        </div>
      </div>

      <!-- 近 7 天错题趋势 -->
      <div class="card" v-if="data.mistake_trend_7d.length">
        <div class="card-title">近 7 天错题录入</div>
        <div class="trend-wrap">
          <svg viewBox="0 0 280 100" class="trend">
            <polyline :points="trendPoints" class="trend-line" />
            <circle
              v-for="(p, i) in trendCoords"
              :key="i"
              :cx="p.x" :cy="p.y" r="3"
              class="trend-dot"
            />
            <text
              v-for="(p, i) in trendCoords"
              :key="'t' + i"
              :x="p.x" :y="92"
              class="trend-label"
            >{{ p.label }}</text>
          </svg>
        </div>
      </div>

      <!-- AI 建议 -->
      <div class="card suggest" v-if="data.ai_suggestion">
        <div class="card-title"><van-icon name="bulb-o" /> AI 学习建议</div>
        <div class="md-body suggest-text" v-html="renderMarkdown(data.ai_suggestion)"></div>
      </div>

      <!-- 最近动态 -->
      <div class="card" v-if="data.recent_documents.length || data.recent_mistakes.length">
        <div class="card-title">最近动态</div>
        <van-cell-group inset>
          <van-cell
            v-for="(d, i) in data.recent_documents"
            :key="'d' + i"
            :title="d.title"
            icon="description"
            is-link
            @click="go('knowledge')"
          />
          <van-cell
            v-for="(m, i) in data.recent_mistakes"
            :key="'m' + i"
            :title="m.question"
            :label="m.subject"
            icon="warning-o"
            is-link
            @click="go('mistakes')"
          />
        </van-cell-group>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getOverview, type StatsOverview } from '@/api/stats'
import { renderMarkdown } from '@/utils/markdown'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const data = ref<StatsOverview>({
  document_count: 0, chunk_count: 0, entity_count: 0, relation_count: 0,
  mistake_total: 0, mistake_mastered: 0, mastery_rate: 0,
  entity_label_dist: [], mistake_subject_dist: [], mistake_trend_7d: [],
  quiz_total: 0, knowledge_mastery: [], mastered_entity_count: 0, study_hours: 0,
  ability_radar: [], recent_documents: [], recent_mistakes: [], ai_suggestion: '', today_goal: '',
})

const nickname = computed(() => auth.user?.display_name || auth.user?.email?.split('@')[0] || '同学')
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const circumference = 2 * Math.PI * 52

function barColor(v: number) {
  if (v >= 80) return '#07c160'
  if (v >= 50) return '#1989fa'
  return '#ee0a24'
}

// 雷达图几何
const radarAxes = computed(() => {
  const items = data.value.ability_radar
  const n = items.length
  const cx = 100, cy = 100, R = 78
  return items.map((_, i) => {
    const ang = (Math.PI * 2 * i) / n - Math.PI / 2
    const x2 = cx + R * Math.cos(ang)
    const y2 = cy + R * Math.sin(ang)
    const lx = cx + (R + 14) * Math.cos(ang)
    const ly = cy + (R + 14) * Math.sin(ang) + 4
    return { x1: cx, y1: cy, x2, y2, lx, ly }
  })
})
const radarRings = computed(() => {
  const n = data.value.ability_radar.length
  if (!n) return []
  const cx = 100, cy = 100, R = 78
  return [0.25, 0.5, 0.75, 1].map((scale) =>
    data.value.ability_radar.map((_, i) => {
      const ang = (Math.PI * 2 * i) / n - Math.PI / 2
      return `${cx + R * scale * Math.cos(ang)},${cy + R * scale * Math.sin(ang)}`
    }).join(' '),
  )
})
const radarPolygon = computed(() => {
  const n = data.value.ability_radar.length
  if (!n) return ''
  const cx = 100, cy = 100, R = 78
  return data.value.ability_radar.map((item, i) => {
    const ang = (Math.PI * 2 * i) / n - Math.PI / 2
    const r = (Math.max(0, Math.min(100, item.count)) / 100) * R
    return `${cx + r * Math.cos(ang)},${cy + r * Math.sin(ang)}`
  }).join(' ')
})

// 趋势折线几何
const trendCoords = computed(() => {
  const items = data.value.mistake_trend_7d
  if (!items.length) return []
  const max = Math.max(1, ...items.map((i) => i.count))
  const W = 280, H = 80, padX = 16
  const step = (W - padX * 2) / Math.max(1, items.length - 1)
  return items.map((it, i) => ({
    x: padX + step * i,
    y: H - (it.count / max) * (H - 10) - 6,
    label: it.date.slice(5),
  }))
})
const trendPoints = computed(() => trendCoords.value.map((p) => `${p.x},${p.y}`).join(' '))

function go(name: string) {
  router.push('/' + name)
}

async function load() {
  loading.value = true
  try {
    data.value = await getOverview()
  } catch {
    showToast('加载学习数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped lang="scss">
.study-center {
  min-height: calc(100vh - 50px);
  padding-bottom: 16px;
}

.loading-wrap {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}

.hero {
  padding: 20px 16px 16px;
  background: linear-gradient(135deg, #1989fa, #5cadff);
  color: #fff;

  .greeting { font-size: 20px; font-weight: 700; }
  .today-goal {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 10px;
    font-size: 13px;
    background: rgba(255, 255, 255, 0.18);
    padding: 8px 10px;
    border-radius: 8px;
  }
  .study-hours {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 8px;
    font-size: 12px;
    opacity: 0.9;
  }
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 16px;
  margin-top: -12px;

  .ov-card {
    background: var(--kg-card);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);

    .ov-num { font-size: 24px; font-weight: 700; color: var(--kg-primary); }
    .ov-label { font-size: 12px; color: var(--kg-text-secondary); margin-top: 4px; }
  }
}

.card {
  margin: 12px 16px;
  background: var(--kg-card);
  border-radius: 12px;
  padding: 16px;

  .card-title {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
}

.mastery-ring {
  position: relative;
  width: 140px;
  height: 140px;
  margin: 0 auto;

  .ring { width: 140px; height: 140px; transform: rotate(-90deg); }
  .ring-bg { fill: none; stroke: #ebedf0; stroke-width: 10; }
  .ring-fg {
    fill: none;
    stroke: #1989fa;
    stroke-width: 10;
    stroke-linecap: round;
    transition: stroke-dashoffset 0.6s ease;
  }
  .ring-text {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;

    .ring-pct { font-size: 26px; font-weight: 700; color: var(--kg-primary); }
    .ring-sub { font-size: 11px; color: var(--kg-text-secondary); margin-top: 2px; }
  }
}

.mastery-item {
  margin-bottom: 14px;
  &:last-child { margin-bottom: 0; }

  .mi-head {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    margin-bottom: 6px;

    .mi-name { color: var(--kg-text); }
    .mi-val { color: var(--kg-text-secondary); font-weight: 600; }
  }
  .mi-sub { font-size: 11px; color: var(--kg-text-secondary); margin-top: 4px; }
}

.radar-wrap { display: flex; justify-content: center; }
.radar { width: 240px; height: 240px; }
.radar-grid { fill: none; stroke: #ebedf0; stroke-width: 1; }
.radar-line { stroke: #ebedf0; stroke-width: 1; }
.radar-area { fill: rgba(25, 137, 250, 0.18); stroke: #1989fa; stroke-width: 2; }
.radar-label { font-size: 10px; fill: var(--kg-text-secondary); text-anchor: middle; }

.trend-wrap { overflow-x: auto; }
.trend { width: 100%; height: 100px; }
.trend-line { fill: none; stroke: #1989fa; stroke-width: 2; }
.trend-dot { fill: #1989fa; }
.trend-label { font-size: 9px; fill: var(--kg-text-secondary); text-anchor: middle; }

.suggest {
  .suggest-text {
    font-size: 14px;
    line-height: 1.7;
    color: var(--kg-text);
  }
}
</style>
