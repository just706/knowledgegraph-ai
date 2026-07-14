<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  generateQuiz,
  gradeQuiz,
  type QuizQuestion,
  type QuizSource,
  type QuizType,
  type QuizAnswerItem,
  type QuizSubmitResponse,
} from '@/api/quiz'

const route = useRoute()

const SOURCE_OPTIONS: { label: string; value: QuizSource }[] = [
  { label: '知识库文档', value: 'knowledge' },
  { label: '错题本薄弱点', value: 'mistakes' },
  { label: '知识图谱', value: 'graph' },
]
const TYPE_OPTIONS: { label: string; value: QuizType }[] = [
  { label: '单选题', value: 'choice' },
  { label: '填空题', value: 'fill' },
  { label: '判断题', value: 'judgment' },
  { label: '简答题', value: 'short' },
]

const selectedSources = ref<QuizSource[]>(['knowledge', 'mistakes', 'graph'])
const selectedTypes = ref<QuizType[]>(['choice'])
const count = ref(5)
const subject = ref('')

onMounted(() => {
  const q = route.query.subject
  if (typeof q === 'string' && q.trim()) {
    subject.value = q.trim()
  }
})

const generating = ref(false)
const questions = ref<QuizQuestion[]>([])
const userAnswers = ref<Record<number, string>>({})
const mode = ref('')

const result = ref<QuizSubmitResponse | null>(null)
const submitted = ref(false)

const sourceTagType: Record<QuizSource, string> = {
  knowledge: 'primary',
  mistakes: 'danger',
  graph: 'success',
}
const sourceLabel: Record<QuizSource, string> = {
  knowledge: '知识库',
  mistakes: '错题本',
  graph: '知识图谱',
}

const canGenerate = computed(() => selectedSources.value.length > 0 && count.value >= 1)

async function handleGenerate() {
  if (!canGenerate.value) {
    ElMessage.warning('请至少选择一个出题来源')
    return
  }
  generating.value = true
  questions.value = []
  userAnswers.value = {}
  result.value = null
  submitted.value = false
  try {
    const res = await generateQuiz({
      sources: selectedSources.value,
      q_types: selectedTypes.value.length ? selectedTypes.value : ['choice'],
      count: count.value,
      subject: subject.value.trim() || null,
    })
    questions.value = res.questions
    mode.value = res.mode
    if (!res.questions.length) {
      ElMessage.warning('未能生成题目，请检查资料是否充足')
    } else {
      ElMessage.success(res.message)
    }
  } catch {
    // 错误由拦截器提示
  } finally {
    generating.value = false
  }
}

function answerOf(i: number): string {
  return userAnswers.value[i] ?? ''
}

async function handleSubmit() {
  if (!questions.value.length) return
  const unanswered = questions.value.some((_, i) => !answerOf(i).trim())
  if (unanswered) {
    ElMessage.warning('还有题目未作答')
    return
  }
  const answers: QuizAnswerItem[] = questions.value.map((q, i) => ({
    question: q.question,
    user_answer: answerOf(i),
    answer: q.answer,
    source: q.source,
    subject: q.subject,
    explanation: q.explanation,
  }))
  try {
    const res = await gradeQuiz({ answers })
    result.value = res
    submitted.value = true
    if (res.wrong_items.length) {
      ElMessage.success(`答题完成，得分 ${res.score}。答错的 ${res.wrong} 题已自动加入错题本`)
    } else {
      ElMessage.success(`满分！得分 ${res.score}，全部正确`)
    }
  } catch {
    // 错误由拦截器提示
  }
}

function reset() {
  questions.value = []
  userAnswers.value = {}
  result.value = null
  submitted.value = false
}
</script>

<template>
  <div class="quiz">
    <div class="quiz__header">
      <div>
        <h2 class="quiz__title">智能出题</h2>
        <p class="quiz__sub">基于你的知识库、错题本与知识图谱自动生成练习，答错的题自动收入错题本</p>
      </div>
    </div>

    <!-- 出题配置 -->
    <el-card v-if="!questions.length" class="quiz__config">
      <el-form label-position="top">
        <el-form-item label="出题来源（可多选）">
          <el-checkbox-group v-model="selectedSources">
            <el-checkbox v-for="s in SOURCE_OPTIONS" :key="s.value" :value="s.value">
              {{ s.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="题型（可多选）">
          <el-checkbox-group v-model="selectedTypes">
            <el-checkbox v-for="t in TYPE_OPTIONS" :key="t.value" :value="t.value">
              {{ t.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="题目数量">
          <el-input-number v-model="count" :min="1" :max="20" />
        </el-form-item>
        <el-form-item label="限定主题（可选）">
          <el-input v-model="subject" placeholder="如：深度学习 / 数学，留空则不限" style="max-width: 280px" />
        </el-form-item>
        <el-button type="primary" :loading="generating" :disabled="!canGenerate" @click="handleGenerate">
          {{ generating ? '正在生成…' : '生成练习题' }}
        </el-button>
      </el-form>
    </el-card>

    <!-- 答题区 -->
    <template v-else>
      <div v-if="mode === 'local'" class="quiz__modehint">
        <el-tag type="info" size="small">本地演示模式</el-tag>
        未配置 LLM，已用模板题演示；配置 API Key 后可生成更丰富的智能题型。
      </div>

      <el-card
        v-for="(q, i) in questions"
        :key="i"
        class="quiz__q"
        :body-style="{ padding: '16px 20px' }"
      >
        <div class="quiz__q-head">
          <span class="quiz__q-no">第 {{ i + 1 }} 题</span>
          <el-tag :type="sourceTagType[q.source as QuizSource]" size="small">
            {{ sourceLabel[q.source as QuizSource] }}
          </el-tag>
          <el-tag size="small" effect="plain">{{ q.q_type }}</el-tag>
          <span class="quiz__stars" title="难度">
            <span
              v-for="n in 5"
              :key="n"
              :class="['quiz__star', { 'is-on': n <= (q.difficulty || 2) }]"
            >★</span>
          </span>
          <span v-if="q.knowledge_point" class="quiz__q-kp">知识点：{{ q.knowledge_point }}</span>
          <span v-if="q.subject" class="quiz__q-subject">{{ q.subject }}</span>
        </div>
        <p class="quiz__q-text">{{ q.question }}</p>

        <!-- 选择题：可点色块 -->
        <div v-if="q.q_type === 'choice' && q.options.length" class="quiz__blocks">
          <button
            v-for="(opt, oi) in q.options"
            :key="oi"
            type="button"
            class="quiz__block"
            :class="{
              'is-selected': userAnswers[i] === opt,
              'is-correct': submitted && result && opt === q.answer,
              'is-wrong': submitted && result && userAnswers[i] === opt && opt !== q.answer,
            }"
            :disabled="submitted"
            @click="userAnswers[i] = opt"
          >
            <span class="quiz__block-tag">{{ String.fromCharCode(65 + oi) }}</span>
            <span class="quiz__block-text">{{ opt }}</span>
          </button>
        </div>

        <!-- 判断题：两个大色块 -->
        <div v-else-if="q.q_type === 'judgment'" class="quiz__blocks quiz__blocks--row">
          <button
            v-for="val in ['正确', '错误']"
            :key="val"
            type="button"
            class="quiz__block"
            :class="{
              'is-selected': userAnswers[i] === val,
              'is-correct': submitted && result && val === q.answer,
              'is-wrong': submitted && result && userAnswers[i] === val && val !== q.answer,
            }"
            :disabled="submitted"
            @click="userAnswers[i] = val"
          >
            <span class="quiz__block-text">{{ val }}</span>
          </button>
        </div>

        <!-- 填空 / 简答：输入框 -->
        <el-input
          v-else
          v-model="userAnswers[i]"
          type="textarea"
          :rows="2"
          :disabled="submitted"
          :placeholder="q.q_type === 'fill' ? '请填写答案' : '请输入你的作答'"
        />

        <!-- 判分后展示解析 -->
        <div v-if="submitted && result" class="quiz__result">
          <el-divider />
          <span :class="result.wrong_items.some((w) => w.question === q.question) ? 'is-wrong' : 'is-right'">
            {{ result.wrong_items.some((w) => w.question === q.question) ? '✗ 答错' : '✓ 正确' }}
          </span>
          <div class="quiz__answer"><b>参考答案：</b>{{ q.answer }}</div>
          <div v-if="q.explanation" class="quiz__explain">{{ q.explanation }}</div>
        </div>
      </el-card>

      <div class="quiz__actions">
        <el-button @click="reset">重新配置</el-button>
        <el-button type="primary" :disabled="submitted" @click="handleSubmit">提交并判分</el-button>
      </div>

      <!-- 成绩汇总 -->
      <el-alert
        v-if="submitted && result"
        class="quiz__score"
        :title="`本次得分 ${result.score} 分（正确 ${result.correct} / 共 ${result.total}，答错 ${result.wrong} 题已加入错题本）`"
        :type="result.score >= 60 ? 'success' : 'warning'"
        :closable="false"
        show-icon
      />
    </template>
  </div>
</template>

<style scoped>
.quiz__title {
  margin: 0;
  font-size: 20px;
}
.quiz__sub {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
  font-size: 13px;
}
.quiz__config {
  max-width: 640px;
}
.quiz__modehint {
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.quiz__q {
  margin-bottom: 16px;
}
.quiz__q-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.quiz__q-no {
  font-weight: 600;
}
.quiz__q-subject {
  color: var(--color-text-secondary);
  font-size: 13px;
}
.quiz__stars {
  display: inline-flex;
  gap: 1px;
  font-size: 13px;
  line-height: 1;
}
.quiz__star {
  color: #dcdfe6;
}
.quiz__star.is-on {
  color: #f7ba2a;
}
.quiz__q-kp {
  font-size: 13px;
  color: var(--el-color-primary);
  background: #ecf3ff;
  border-radius: 4px;
  padding: 1px 8px;
}
.quiz__q-text {
  margin: 0 0 12px;
  line-height: 1.7;
  white-space: pre-wrap;
}
.quiz__blocks {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.quiz__blocks--row {
  flex-direction: row;
}
.quiz__block {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  text-align: left;
  padding: 12px 14px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  transition: all 0.15s ease;
}
.quiz__blocks--row .quiz__block {
  width: auto;
  min-width: 120px;
  justify-content: center;
}
.quiz__block:hover:not(:disabled) {
  border-color: var(--el-color-primary);
  background: #f5f8ff;
}
.quiz__block.is-selected {
  border-color: var(--el-color-primary);
  background: #ecf3ff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15);
}
.quiz__block.is-correct {
  border-color: #67c23a;
  background: #f0f9eb;
  color: #529b2e;
}
.quiz__block.is-wrong {
  border-color: #f56c6c;
  background: #fef0f0;
  color: #c45656;
}
.quiz__block:disabled {
  cursor: default;
}
.quiz__block-tag {
  flex: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #f0f2f5;
  color: #909399;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}
.quiz__block.is-selected .quiz__block-tag {
  background: var(--el-color-primary);
  color: #fff;
}
.quiz__block.is-correct .quiz__block-tag {
  background: #67c23a;
  color: #fff;
}
.quiz__block.is-wrong .quiz__block-tag {
  background: #f56c6c;
  color: #fff;
}
.quiz__block-text {
  white-space: pre-wrap;
  word-break: break-word;
}
.quiz__result {
  font-size: 14px;
}
.is-right {
  color: #67c23a;
  font-weight: 600;
}
.is-wrong {
  color: #f56c6c;
  font-weight: 600;
}
.quiz__answer {
  margin-top: 6px;
  line-height: 1.6;
}
.quiz__explain {
  margin-top: 6px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}
.quiz__actions {
  display: flex;
  gap: 12px;
  margin: 8px 0 16px;
}
.quiz__score {
  margin-top: 8px;
}
</style>
