<template>
  <div class="quiz-view">
    <van-nav-bar :title="phase === 'result' ? '练习结果' : phase === 'answering' ? '作答中' : '智能练习'" />

    <!-- 设置阶段 -->
    <div v-if="phase === 'setup'" class="setup">
      <van-cell-group inset>
        <van-field
          v-model="sourceLabel"
          label="出题来源"
          readonly
          is-link
          @click="showSource = true"
        />
        <van-field
          v-model="category"
          label="分类筛选"
          placeholder="选填，按学科筛选"
        />
        <van-field
          v-model="countLabel"
          label="题目数量"
          readonly
          is-link
          @click="showCount = true"
        />
        <van-cell title="题型">
          <template #value>
            <van-checkbox-group v-model="selectedTypes" direction="horizontal">
              <van-checkbox name="choice">选择题</van-checkbox>
              <van-checkbox name="fill">填空题</van-checkbox>
              <van-checkbox name="judgment">判断题</van-checkbox>
              <van-checkbox name="short">简答题</van-checkbox>
            </van-checkbox-group>
          </template>
        </van-cell>
      </van-cell-group>

      <div class="start-btn">
        <van-button round block type="primary" :loading="generating" @click="generate">
          开始练习
        </van-button>
      </div>
    </div>

    <!-- 作答阶段 -->
    <div v-else-if="phase === 'answering'" class="answering">
      <div class="progress">{{ currentIndex + 1 }} / {{ quizzes.length }}</div>
      <div class="question-card">
        <h3>{{ currentQuiz.question }}</h3>
        <template v-if="currentQuiz.q_type === 'choice' && currentQuiz.options">
          <van-radio-group v-model="currentAnswer">
            <van-radio v-for="opt in currentQuiz.options" :key="opt" :name="opt">{{ opt }}</van-radio>
          </van-radio-group>
        </template>
        <template v-else>
          <van-field
            v-model="currentAnswer"
            type="textarea"
            rows="3"
            placeholder="请输入答案"
          />
        </template>
      </div>
      <van-button round block type="primary" @click="nextQuestion">
        {{ currentIndex + 1 === quizzes.length ? '提交' : '下一题' }}
      </van-button>
    </div>

    <!-- 结果阶段 -->
    <div v-else class="result">
      <van-circle
        :current="result?.score || 0"
        :rate="100"
        :text="`${result?.score || 0}分`"
        size="120"
      />
      <p>正确 {{ result?.correct }} / {{ result?.total }}</p>

      <van-cell-group inset class="detail-list">
        <van-cell v-for="d in result?.details" :key="d.quiz_id" :title="d.question">
          <template #label>
            <span :class="d.is_correct ? 'correct' : 'wrong'">
              {{ d.is_correct ? '✓ 正确' : '✗ 错误' }}
            </span>
            <br />
            正确答案: {{ d.correct_answer }}
            <br />
            <span v-if="d.explanation" class="exp md-body" v-html="renderMarkdown(d.explanation)"></span>
          </template>
        </van-cell>
      </van-cell-group>

      <van-button round block type="primary" @click="reset">再来一组</van-button>
    </div>

    <!-- 弹窗 -->
    <van-popup v-model:show="showSource" position="bottom" round>
      <van-picker
        :columns="sourceColumns"
        @confirm="onSourceConfirm"
        @cancel="showSource = false"
      />
    </van-popup>
    <van-popup v-model:show="showCount" position="bottom" round>
      <van-picker
        :columns="countColumns"
        @confirm="onCountConfirm"
        @cancel="showCount = false"
      />
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { showToast } from 'vant'
import { generateQuizzes, submitQuiz, type QuizItem, type SubmitResult, type QuizSource, type QuizType } from '@/api/quiz'
import { renderMarkdown } from '@/utils/markdown'

type Phase = 'setup' | 'answering' | 'result'
const phase = ref<Phase>('setup')

const sourceMap: Record<string, QuizSource> = { 知识库: 'knowledge', 错题本: 'mistakes', 知识图谱: 'graph' }
const sourceColumns = [{ values: Object.keys(sourceMap) }]
const sourceLabel = ref('知识库')
const showSource = ref(false)

const countColumns = [{ values: [5, 10, 15, 20] }]
const countLabel = ref('5')
const showCount = ref(false)

const category = ref('')
const selectedTypes = ref<QuizType[]>(['choice', 'fill', 'judgment', 'short'])

const quizzes = ref<QuizItem[]>([])
const currentIndex = ref(0)
const answers = ref<Record<number, string>>({})
const currentAnswer = ref('')
const generating = ref(false)

const currentQuiz = computed(() => quizzes.value[currentIndex.value] || {} as QuizItem)
const result = ref<SubmitResult | null>(null)

function onSourceConfirm({ selectedValues }: { selectedValues: string[] }) {
  sourceLabel.value = selectedValues[0]
  showSource.value = false
}

function onCountConfirm({ selectedValues }: { selectedValues: (number | string)[] }) {
  countLabel.value = String(selectedValues[0])
  showCount.value = false
}

async function generate() {
  generating.value = true
  try {
    quizzes.value = await generateQuizzes({
      source: sourceMap[sourceLabel.value],
      q_types: selectedTypes.value,
      count: Number(countLabel.value),
      category: category.value || undefined,
    })
    if (quizzes.value.length === 0) {
      showToast('暂无题目，请换来源或上传资料')
      return
    }
    phase.value = 'answering'
    currentIndex.value = 0
    answers.value = {}
    currentAnswer.value = ''
  } catch {
    // error toast
  } finally {
    generating.value = false
  }
}

function nextQuestion() {
  if (!currentAnswer.value.trim()) {
    showToast('请输入答案')
    return
  }
  answers.value[currentQuiz.value.id] = currentAnswer.value
  if (currentIndex.value + 1 >= quizzes.value.length) {
    submit()
  } else {
    currentIndex.value++
    currentAnswer.value = ''
  }
}

async function submit() {
  try {
    const res = await submitQuiz({
      answers: quizzes.value.map((q) => ({ quiz_id: q.id, user_answer: answers.value[q.id] || '' })),
    })
    result.value = res
    phase.value = 'result'
  } catch {
    // error toast
  }
}

function reset() {
  phase.value = 'setup'
  quizzes.value = []
  result.value = null
}
</script>

<style scoped lang="scss">
.quiz-view {
  min-height: calc(100vh - 50px);
  padding-bottom: 20px;
}

.setup {
  padding-top: 16px;
}

.start-btn {
  padding: 24px 16px;
}

.answering {
  padding: 16px;

  .progress {
    text-align: center;
    color: var(--kg-text-secondary);
    margin-bottom: 16px;
  }

  .question-card {
    background: var(--kg-card);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 24px;

    h3 {
      margin-top: 0;
      line-height: 1.6;
    }
  }
}

.result {
  padding: 24px 16px;
  text-align: center;

  .detail-list {
    margin: 24px 0;
    text-align: left;

    .correct { color: #07c160; }
    .wrong { color: #ee0a24; }
    .exp { color: var(--kg-text-secondary); }
  }
}
</style>
