<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listMistakes,
  listSubjects,
  createMistake,
  updateMistake,
  deleteMistake,
  explainMistake,
  analyzeWeakness,
  type MistakeItem,
  type MistakeCreate,
} from '@/api/mistake'

const router = useRouter()

const mistakes = ref<MistakeItem[]>([])
const subjects = ref<string[]>([])
const loading = ref(false)
const onlyUnmastered = ref(false)
const subjectFilter = ref<string>('')

// 新建 / 编辑抽屉
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = ref<MistakeCreate & { id?: number }>({
  question: '',
  my_answer: '',
  correct_answer: '',
  error_reason: '',
  subject: '',
})

// 解析抽屉
const explainVisible = ref(false)
const explaining = ref(false)
const currentExplain = ref<MistakeItem | null>(null)
const explanationText = ref('')
const explanationMode = ref('')

// 薄弱点分析抽屉
const weaknessVisible = ref(false)
const analyzing = ref(false)
const weaknessText = ref('')
const weaknessMode = ref('')

const totalCount = computed(() => mistakes.value.length)
const unmasteredCount = computed(() => mistakes.value.filter((m) => !m.mastered).length)

async function fetchMistakes() {
  loading.value = true
  try {
    mistakes.value = await listMistakes({
      unmastered: onlyUnmastered.value || undefined,
      subject: subjectFilter.value || undefined,
    })
  } finally {
    loading.value = false
  }
}

async function fetchSubjects() {
  try {
    subjects.value = await listSubjects()
  } catch {
    subjects.value = []
  }
}

function openCreate() {
  editingId.value = null
  form.value = { question: '', my_answer: '', correct_answer: '', error_reason: '', subject: '' }
  formVisible.value = true
}

function openEdit(item: MistakeItem) {
  editingId.value = item.id
  form.value = {
    id: item.id,
    question: item.question,
    my_answer: item.my_answer,
    correct_answer: item.correct_answer,
    error_reason: item.error_reason,
    subject: item.subject,
  }
  formVisible.value = true
}

async function saveForm() {
  if (!form.value.question.trim()) {
    ElMessage.warning('请填写题目/知识点')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateMistake(editingId.value, {
        question: form.value.question,
        my_answer: form.value.my_answer,
        correct_answer: form.value.correct_answer,
        error_reason: form.value.error_reason,
        subject: form.value.subject,
      })
      ElMessage.success('已更新')
    } else {
      await createMistake({
        question: form.value.question,
        my_answer: form.value.my_answer,
        correct_answer: form.value.correct_answer,
        error_reason: form.value.error_reason,
        subject: form.value.subject,
      })
      ElMessage.success('已加入错题本')
    }
    formVisible.value = false
    await Promise.all([fetchMistakes(), fetchSubjects()])
  } finally {
    saving.value = false
  }
}

async function toggleMastered(item: MistakeItem) {
  await updateMistake(item.id, { mastered: !item.mastered, review_count: item.review_count + 1 })
  ElMessage.success(item.mastered ? '已标为未掌握' : '已掌握，真棒！')
  await fetchMistakes()
}

async function handleDelete(item: MistakeItem) {
  try {
    await ElMessageBox.confirm('确认删除这条错题？', '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteMistake(item.id)
  ElMessage.success('已删除')
  await fetchMistakes()
}

async function openExplain(item: MistakeItem) {
  currentExplain.value = item
  explainVisible.value = true
  explanationText.value = ''
  explaining.value = true
  try {
    const res = await explainMistake(item.id)
    explanationText.value = res.explanation
    explanationMode.value = res.mode
  } catch {
    // 错误由拦截器提示
  } finally {
    explaining.value = false
  }
}

function askAI(item: MistakeItem) {
  const q = `请帮我详细讲解这道错题：${item.question}`
  router.push({ name: 'chat', query: { q } })
}

async function openWeakness() {
  weaknessVisible.value = true
  weaknessText.value = ''
  analyzing.value = true
  weaknessMode.value = ''
  try {
    const res = await analyzeWeakness()
    weaknessText.value = res.analysis
    weaknessMode.value = res.mode
  } catch {
    // 错误由拦截器提示
  } finally {
    analyzing.value = false
  }
}

onMounted(() => {
  fetchMistakes()
  fetchSubjects()
})
</script>

<template>
  <div class="mistakes">
    <div class="mistakes__header">
      <div>
        <h2 class="mistakes__title">错题本</h2>
        <p class="mistakes__sub">
          共 {{ totalCount }} 题，未掌握 {{ unmasteredCount }} 题
        </p>
      </div>
      <el-button type="primary" @click="openCreate">+ 新增错题</el-button>
      <el-button :loading="analyzing" @click="openWeakness">AI 分析薄弱点</el-button>
    </div>

    <div class="mistakes__filters">
      <el-checkbox v-model="onlyUnmastered" @change="fetchMistakes">只看未掌握</el-checkbox>
      <el-select
        v-model="subjectFilter"
        placeholder="全部主题"
        clearable
        style="width: 160px; margin-left: 12px"
        @change="fetchMistakes"
      >
        <el-option v-for="s in subjects" :key="s" :label="s" :value="s" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="mistakes" empty-text="还没有错题，点击右上角新增">
      <el-table-column prop="question" label="题目 / 知识点" min-width="220" show-overflow-tooltip />
      <el-table-column prop="subject" label="主题" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.subject" size="small" effect="plain">{{ row.subject }}</el-tag>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.mastered ? 'success' : 'warning'" size="small">
            {{ row.mastered ? '已掌握' : '未掌握' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="复习" width="70" align="center">
        <template #default="{ row }">{{ row.review_count }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openExplain(row)">AI 解析</el-button>
          <el-button link type="primary" @click="toggleMastered(row)">
            {{ row.mastered ? '标未掌握' : '标记掌握' }}
          </el-button>
          <el-button link type="primary" @click="askAI(row)">追问</el-button>
          <el-button link type="info" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建 / 编辑 -->
    <el-drawer v-model="formVisible" :title="editingId ? '编辑错题' : '新增错题'" size="460px">
      <el-form label-position="top">
        <el-form-item label="题目 / 知识点 *">
          <el-input v-model="form.question" type="textarea" :rows="3" placeholder="如：为什么 CNN 适合处理图像？" />
        </el-form-item>
        <el-form-item label="我的答案">
          <el-input v-model="form.my_answer" type="textarea" :rows="2" placeholder="当时怎么答的" />
        </el-form-item>
        <el-form-item label="正确答案 / 要点">
          <el-input v-model="form.correct_answer" type="textarea" :rows="2" placeholder="正确思路或答案" />
        </el-form-item>
        <el-form-item label="错误原因 / 反思">
          <el-input v-model="form.error_reason" type="textarea" :rows="2" placeholder="错在哪里" />
        </el-form-item>
        <el-form-item label="主题标签">
          <el-input v-model="form.subject" placeholder="如：深度学习 / 数学" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveForm">保存</el-button>
      </template>
    </el-drawer>

    <!-- AI 解析 -->
    <el-drawer v-model="explainVisible" title="AI 错题诊断" size="520px">
      <div v-if="currentExplain" class="explain">
        <div class="explain__q"><b>题目：</b>{{ currentExplain.question }}</div>
        <el-divider />
        <div v-if="explaining" class="muted">AI 正在生成诊断…</div>
        <div v-else>
          <el-tag v-if="explanationMode === 'llm'" type="success" size="small">AI 语义解析</el-tag>
          <el-tag v-else type="info" size="small">本地模式</el-tag>
          <pre class="explain__text">{{ explanationText }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="explainVisible = false">关闭</el-button>
        <el-button v-if="currentExplain" type="primary" @click="askAI(currentExplain)">
          去 AI 问答追问
        </el-button>
      </template>
    </el-drawer>

    <!-- AI 薄弱点分析 -->
    <el-drawer v-model="weaknessVisible" title="AI 学习薄弱点分析" size="520px">
      <div v-if="analyzing" class="muted">AI 正在分析你的错题…</div>
      <div v-else>
        <el-tag v-if="weaknessMode === 'llm'" type="success" size="small">AI 语义分析</el-tag>
        <el-tag v-else type="info" size="small">本地模式</el-tag>
        <pre class="explain__text">{{ weaknessText }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.mistakes__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mistakes__title {
  margin: 0;
  font-size: 20px;
}
.mistakes__sub {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
  font-size: 13px;
}
.mistakes__filters {
  margin: 16px 0;
}
.muted {
  color: var(--color-text-secondary);
}
.explain__q {
  font-size: 14px;
  line-height: 1.6;
}
.explain__text {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.7;
  background: #f7f8fa;
  padding: 12px;
  border-radius: 8px;
}
</style>
