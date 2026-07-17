<template>
  <div class="mistake-view">
    <van-nav-bar
      :title="`错题本 (${unmasteredCount})`"
      right-text="薄弱点"
      @click-right="openWeakness"
    />

    <div class="filter-bar">
      <van-dropdown-menu>
        <van-dropdown-item v-model="filterMastered" :options="masteredOptions" @change="load" />
        <van-dropdown-item v-model="filterSubject" :options="subjectOptions" @change="load" />
      </van-dropdown-menu>
    </div>

    <van-pull-refresh v-model="refreshing" @refresh="load">
      <van-list>
        <van-swipe-cell v-for="m in mistakes" :key="m.id">
          <van-cell :title="m.question" :label="m.subject || '未分类'" clickable @click="openDetail(m)">
            <template #value>
              <van-tag :type="m.mastered ? 'success' : 'danger'">
                {{ m.mastered ? '已掌握' : '待复习' }}
              </van-tag>
            </template>
          </van-cell>
          <template #right>
            <van-button square type="primary" text="复习" @click="review(m.id)" />
            <van-button square type="danger" text="删除" @click="remove(m.id)" />
          </template>
        </van-swipe-cell>
        <van-empty v-if="mistakes.length === 0" description="暂无错题" />
      </van-list>
    </van-pull-refresh>

    <!-- 详情弹窗 -->
    <van-popup v-model:show="showDetail" position="bottom" round :style="{ height: '70%' }">
      <div class="detail-panel" v-if="activeMistake">
        <h3>{{ activeMistake.question }}</h3>
        <div class="row"><b>我的答案:</b> {{ activeMistake.my_answer }}</div>
        <div class="row"><b>正确答案:</b> <span class="correct">{{ activeMistake.correct_answer }}</span></div>
        <div class="row" v-if="activeMistake.error_reason"><b>错误原因:</b> {{ activeMistake.error_reason }}</div>

        <div class="detail-actions">
          <van-button type="primary" block round :loading="explaining" @click="getExplain">
            AI 智能解析
          </van-button>
          <div v-if="explainResult" class="explain-box md-body" v-html="renderMarkdown(explainResult.explanation + (explainResult.suggestion ? '\n\n**建议**: ' + explainResult.suggestion : ''))"></div>
        </div>
      </div>
    </van-popup>

    <!-- 薄弱点弹窗 -->
    <van-popup v-model:show="showWeakness" position="bottom" round :style="{ height: '50%' }">
      <div class="weakness-panel" v-if="weakness">
        <h3>薄弱点分析</h3>
        <p v-for="(s, i) in weakness.suggestions" :key="i">· {{ s }}</p>
      </div>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { analyzeWeakness } from '@/api/mistake'
import { showToast, showConfirmDialog } from 'vant'
import {
  listMistakes, listSubjects, reviewMistake, explainMistake, deleteMistake,
  type MistakeItem,
} from '@/api/mistake'
import { renderMarkdown } from '@/utils/markdown'

const mistakes = ref<MistakeItem[]>([])
const subjects = ref<string[]>([])
const refreshing = ref(false)

const filterMastered = ref(-1) // -1=全部, 0=未掌握, 1=已掌握
const filterSubject = ref('')
const masteredOptions = [
  { text: '全部', value: -1 },
  { text: '待复习', value: 0 },
  { text: '已掌握', value: 1 },
]
const subjectOptions = computed(() => [{ text: '全部分类', value: '' }, ...subjects.value.map((s) => ({ text: s, value: s }))])

const unmasteredCount = computed(() => mistakes.value.filter((m) => !m.mastered).length)

const showDetail = ref(false)
const activeMistake = ref<MistakeItem | null>(null)
const explaining = ref(false)
const explainResult = ref<{ explanation: string; suggestion?: string | null } | null>(null)
const showWeakness = ref(false)
const weakness = ref<{ weak_subjects: string[]; suggestions: string[] } | null>(null)

async function openWeakness() {
  weakness.value = await analyzeWeakness()
  showWeakness.value = true
}

async function load() {
  const params: { mastered?: boolean; subject?: string } = {}
  if (filterMastered.value === 0) params.mastered = false
  if (filterMastered.value === 1) params.mastered = true
  if (filterSubject.value) params.subject = filterSubject.value
  mistakes.value = await listMistakes(params)
  refreshing.value = false
}

function openDetail(m: MistakeItem) {
  activeMistake.value = m
  explainResult.value = null
  showDetail.value = true
}

async function review(id: number) {
  const m = mistakes.value.find((x) => x.id === id)
  if (m?.mastered) {
    showToast('已掌握')
    return
  }
  const updated = await reviewMistake(id, 'schedule')
  showToast(updated.review_stage > 1 ? '已加入复习计划' : '已开始复习')
  await load()
}

async function remove(id: number) {
  await showConfirmDialog({ title: '确认删除', message: '删除后无法恢复' })
  await deleteMistake(id)
  showToast('已删除')
  await load()
}

async function getExplain() {
  if (!activeMistake.value) return
  explaining.value = true
  try {
    explainResult.value = await explainMistake(activeMistake.value.id)
  } catch {
    // error toast
  } finally {
    explaining.value = false
  }
}

onMounted(async () => {
  await load()
  subjects.value = await listSubjects()
})
</script>

<style scoped lang="scss">
.mistake-view {
  min-height: calc(100vh - 50px);
}

.filter-bar {
  background: var(--kg-card);
}

.detail-panel {
  padding: 20px;

  h3 {
    margin-top: 0;
    line-height: 1.6;
  }

  .row {
    margin: 12px 0;
    line-height: 1.6;
  }

  .correct { color: #07c160; }
}

.detail-actions {
  margin-top: 20px;
}

.explain-box {
  margin-top: 16px;
  padding: 12px;
  background: var(--kg-bg);
  border-radius: 8px;
}

.weakness-panel {
  padding: 20px;

  h3 { margin-top: 0; }
  p { line-height: 1.8; }
}
</style>
