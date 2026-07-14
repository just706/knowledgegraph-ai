<script setup lang="ts">
import { ref, nextTick, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  askQuestion,
  listSessions,
  createSession,
  getSessionMessages,
  deleteSession,
  type ChatSource,
  type ChatMode,
  type ChatSession,
  type ChatMessage,
  type Paginated,
} from '@/api/chat'

const route = useRoute()

interface ChatMessageView {
  id?: number
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
  loading?: boolean
  mode?: ChatMode
  genMode?: 'llm' | 'local' | null
}

const MODE_OPTIONS: { label: string; value: ChatMode }[] = [
  { label: '默认', value: 'normal' },
  { label: '初学者', value: 'beginner' },
  { label: '考试', value: 'exam' },
  { label: '面试', value: 'interview' },
]

const SESSION_PAGE_SIZE = 20
const MESSAGE_PAGE_SIZE = 50

// ---- 会话侧边栏 ----
const sessions = ref<ChatSession[]>([])
const sessionsPage = ref(1)
const sessionsTotal = ref(0)
const sessionsLoading = ref(false)
const currentSessionId = ref<number | null>(null)
const sidebarCollapsed = ref(false)

// ---- 当前会话消息 ----
const messages = ref<ChatMessageView[]>([])
const input = ref('')
const sending = ref(false)
const currentMode = ref<ChatMode>('normal')
const scrollRef = ref<HTMLElement | null>(null)
const loadingHistory = ref(false)

const suggestions = [
  '请帮我总结上传资料的核心要点',
  '资料里提到了哪些关键概念？',
  '用通俗的语言解释一下核心内容',
]

const hasMoreSessions = computed(
  () => sessionsPage.value * SESSION_PAGE_SIZE < sessionsTotal.value,
)

async function scrollToBottom() {
  await nextTick()
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  }
}

// ---- 会话列表加载（分页累加）----
async function loadSessions(reset = false) {
  if (reset) {
    sessionsPage.value = 1
    sessions.value = []
  }
  sessionsLoading.value = true
  try {
    const data: Paginated<ChatSession> = await listSessions(
      sessionsPage.value,
      SESSION_PAGE_SIZE,
    )
    sessionsTotal.value = data.total
    if (reset) {
      sessions.value = data.items
    } else {
      sessions.value.push(...data.items)
    }
  } catch {
    // 拦截器已提示
  } finally {
    sessionsLoading.value = false
  }
}

async function loadMoreSessions() {
  if (sessionsLoading.value || !hasMoreSessions.value) return
  sessionsPage.value += 1
  await loadSessions(false)
}

// ---- 新建会话 ----
async function newSession() {
  try {
    const s = await createSession('新对话')
    sessions.value.unshift(s)
    sessionsTotal.value += 1
    currentSessionId.value = s.id
    messages.value = []
  } catch {
    // 拦截器已提示
  }
}

// ---- 进入某个历史会话，回看消息（分页累加）----
async function openSession(session: ChatSession, reset = true) {
  currentSessionId.value = session.id
  if (reset) messages.value = []
  loadingHistory.value = true
  try {
    const data: Paginated<ChatMessage> = await getSessionMessages(
      session.id,
      reset ? 1 : Math.ceil(messages.value.filter((m) => m.id).length / MESSAGE_PAGE_SIZE) + 1,
      MESSAGE_PAGE_SIZE,
    )
    const mapped: ChatMessageView[] = data.items.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      sources: m.sources as ChatSource[],
      genMode: m.gen_mode,
    }))
    if (reset) {
      messages.value = mapped
    } else {
      // 历史更早的消息插到前面
      messages.value = [...mapped, ...messages.value]
    }
    await scrollToBottom()
  } catch {
    // 拦截器已提示
  } finally {
    loadingHistory.value = false
  }
}

async function deleteSessionById(session: ChatSession) {
  try {
    await deleteSession(session.id)
    sessions.value = sessions.value.filter((s) => s.id !== session.id)
    sessionsTotal.value = Math.max(0, sessionsTotal.value - 1)
    if (currentSessionId.value === session.id) {
      currentSessionId.value = null
      messages.value = []
    }
    ElMessage.success('会话已删除')
  } catch {
    // 拦截器已提示
  }
}

// ---- 发送消息 ----
async function send(text?: string) {
  const query = (text ?? input.value).trim()
  if (!query || sending.value) return

  // 乐观插入用户消息
  messages.value.push({ role: 'user', content: query })
  const assistantMsg: ChatMessageView = {
    role: 'assistant',
    content: '',
    loading: true,
    mode: currentMode.value,
  }
  messages.value.push(assistantMsg)
  input.value = ''
  sending.value = true
  await scrollToBottom()

  try {
    const res = await askQuestion({
      query,
      top_k: 5,
      mode: currentMode.value,
      session_id: currentSessionId.value,
    })
    assistantMsg.content = res.answer
    assistantMsg.sources = res.sources
    assistantMsg.genMode = res.mode
    // 若本次自动创建了会话，记录 id 并更新侧栏标题
    if (currentSessionId.value == null && res.session_id) {
      currentSessionId.value = res.session_id
      await loadSessions(true)
    } else if (res.session_id) {
      // 刷新侧栏标题（首条问题可能更新了标题）
      const idx = sessions.value.findIndex((s) => s.id === res.session_id)
      if (idx >= 0 && sessions.value[idx].title !== res.session_title) {
        sessions.value[idx] = { ...sessions.value[idx], title: res.session_title }
      }
    }
  } catch {
    assistantMsg.content = '抱歉，问答出错了，请稍后重试。'
  } finally {
    assistantMsg.loading = false
    sending.value = false
    await scrollToBottom()
  }
}

onMounted(async () => {
  messages.value.push({
    role: 'assistant',
    content:
      '你好！我是基于你个人知识库的 AI 学习助手。\n上传资料后，直接向我说出你的问题，我会从资料中检索并回答。',
  })
  await loadSessions(true)
  // 思维导图等页面跳转过来时预填问题
  const q = route.query.q
  if (typeof q === 'string' && q.trim()) {
    input.value = q.trim()
  }
})
</script>

<template>
  <div class="chat-layout">
    <!-- 左侧会话栏 -->
    <aside class="chat-side" :class="{ 'chat-side--collapsed': sidebarCollapsed }">
      <div class="chat-side__top">
        <el-button type="primary" class="chat-side__new" @click="newSession">
          + 新建对话
        </el-button>
        <el-button text class="chat-side__toggle" @click="sidebarCollapsed = !sidebarCollapsed">
          {{ sidebarCollapsed ? '»' : '«' }}
        </el-button>
      </div>

      <div v-if="!sidebarCollapsed" class="chat-side__list" v-loading="sessionsLoading">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ 'session-item--active': s.id === currentSessionId }"
          @click="openSession(s)"
        >
          <span class="session-item__title" :title="s.title">{{ s.title }}</span>
          <el-button
            text
            size="small"
            class="session-item__del"
            @click.stop="deleteSessionById(s)"
          >🗑</el-button>
        </div>

        <div v-if="!sessionsLoading && sessions.length === 0" class="chat-side__empty">
          还没有对话
        </div>

        <div v-if="hasMoreSessions" class="chat-side__more">
          <el-button text size="small" :loading="sessionsLoading" @click="loadMoreSessions">
            加载更多
          </el-button>
        </div>
      </div>
    </aside>

    <!-- 右侧对话区 -->
    <section class="chat-main">
      <div class="chat-header">
        <div>
          <h2>AI 学习助手</h2>
          <p class="subtitle">基于你上传的资料（RAG）：检索相关切片 → 生成答案，并附上引用来源。</p>
        </div>
        <div class="mode-switch">
          <span class="mode-switch__label">解释模式</span>
          <el-radio-group v-model="currentMode" size="small">
            <el-radio-button v-for="m in MODE_OPTIONS" :key="m.value" :value="m.value">
              {{ m.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <div class="chat-container">
        <div ref="scrollRef" class="chat-messages" v-loading="loadingHistory">
          <div v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="msg.role">
            <div class="msg-bubble">
              <template v-if="msg.loading">
                <span class="dot-flashing" />
              </template>
              <template v-else>
                <div v-if="msg.role === 'assistant'" class="msg-tags">
                  <span v-if="msg.genMode === 'llm'" class="tag tag--ai">AI 生成</span>
                  <span v-else-if="msg.genMode === 'local'" class="tag tag--local">本地模式</span>
                  <span
                    v-if="msg.mode && msg.mode !== 'normal'"
                    class="tag tag--explain"
                  >{{ MODE_OPTIONS.find((m) => m.value === msg.mode)?.label }}模式</span>
                </div>
                <p class="msg-content">{{ msg.content }}</p>
              </template>

              <div v-if="msg.role === 'assistant' && msg.sources?.length" class="sources">
                <div class="sources-title">引用来源</div>
                <el-collapse>
                  <el-collapse-item
                    v-for="(s, i) in msg.sources"
                    :key="i"
                    :title="`资料 #${s.document_id} · 第 ${s.chunk_index + 1} 段 · 相关度 ${s.score}`"
                  >
                    <p class="source-snippet">{{ s.snippet }}</p>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-suggestions" v-if="messages.length <= 1">
          <el-tag
            v-for="s in suggestions"
            :key="s"
            class="suggest-tag"
            @click="send(s)"
          >
            {{ s }}
          </el-tag>
        </div>

        <div class="chat-input">
          <el-input
            v-model="input"
            type="textarea"
            :rows="2"
            placeholder="输入你的问题，例如：资料的核心观点是什么？"
            @keydown.enter.exact.prevent="send()"
          />
          <el-button type="primary" :loading="sending" @click="send()">
            {{ sending ? '思考中…' : '发送' }}
          </el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.chat-layout {
  display: flex;
  height: calc(100vh - 140px);
  border: 1px solid #ebeef5;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}
.chat-side {
  width: 240px;
  flex-shrink: 0;
  background: #f7f8fa;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
  &.chat-side--collapsed {
    width: 44px;
  }
}
.chat-side__top {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px;
  border-bottom: 1px solid #ebeef5;
}
.chat-side__new {
  flex: 1;
}
.chat-side__toggle {
  flex-shrink: 0;
}
.chat-side__list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  &:hover {
    background: #eceef1;
  }
  &--active {
    background: #e6f0ff;
  }
}
.session-item__title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.session-item__del {
  opacity: 0;
  font-size: 12px;
}
.session-item:hover .session-item__del {
  opacity: 1;
}
.chat-side__empty {
  text-align: center;
  color: #909399;
  font-size: 13px;
  padding: 24px 0;
}
.chat-side__more {
  text-align: center;
  padding: 4px 0 8px;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.chat-header {
  margin: 0;
  padding: 12px 20px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  border-bottom: 1px solid #ebeef5;
  h2 { margin: 0; }
}
.mode-switch {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mode-switch__label {
  font-size: 13px;
  color: #909399;
}
.msg-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}
.tag {
  display: inline-block;
  font-size: 12px;
  border-radius: 4px;
  padding: 1px 8px;
  line-height: 1.6;
}
.tag--ai {
  color: #2e7d32;
  background: #e8f5e9;
}
.tag--local {
  color: #ed6c02;
  background: #fff4e5;
}
.tag--explain {
  color: #409eff;
  background: #ecf3ff;
}
.subtitle {
  color: #888;
  margin: 4px 0 0;
  font-size: 13px;
}
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.msg-row {
  display: flex;
  &.user { justify-content: flex-end; }
  &.assistant { justify-content: flex-start; }
}
.msg-bubble {
  max-width: 78%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
}
.user .msg-bubble {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 2px;
}
.assistant .msg-bubble {
  background: #f4f6f8;
  color: #303133;
  border-bottom-left-radius: 2px;
}
.msg-content { margin: 0; }
.sources {
  margin-top: 10px;
  border-top: 1px dashed #dcdfe6;
  padding-top: 8px;
}
.sources-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}
.source-snippet {
  white-space: pre-wrap;
  line-height: 1.6;
  color: #606266;
  margin: 0;
}
.dot-flashing {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #909399;
  animation: flash 1s infinite alternate;
}
@keyframes flash {
  from { opacity: 0.3; }
  to { opacity: 1; }
}
.chat-suggestions {
  padding: 0 20px 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.suggest-tag {
  cursor: pointer;
}
.chat-input {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  align-items: flex-end;
}
.chat-input .el-button {
  flex-shrink: 0;
}
</style>
