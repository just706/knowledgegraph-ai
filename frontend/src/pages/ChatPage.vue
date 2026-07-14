<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { askQuestion, type ChatSource } from '@/api/chat'

const route = useRoute()

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
  loading?: boolean
}

const messages = ref<ChatMessage[]>([])
const input = ref('')
const sending = ref(false)
const scrollRef = ref<HTMLElement | null>(null)

const suggestions = [
  '请帮我总结上传资料的核心要点',
  '资料里提到了哪些关键概念？',
  '用通俗的语言解释一下核心内容',
]

async function scrollToBottom() {
  await nextTick()
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  }
}

async function send(text?: string) {
  const query = (text ?? input.value).trim()
  if (!query || sending.value) return

  messages.value.push({ role: 'user', content: query })
  const assistantMsg: ChatMessage = { role: 'assistant', content: '', loading: true }
  messages.value.push(assistantMsg)
  input.value = ''
  sending.value = true
  await scrollToBottom()

  try {
    const res = await askQuestion(query)
    assistantMsg.content = res.answer
    assistantMsg.sources = res.sources
  } catch {
    assistantMsg.content = '抱歉，问答出错了，请稍后重试。'
  } finally {
    assistantMsg.loading = false
    sending.value = false
    await scrollToBottom()
  }
}

onMounted(() => {
  messages.value.push({
    role: 'assistant',
    content: '你好！我是基于你个人知识库的 AI 学习助手。\n上传资料后，直接向我说出你的问题，我会从资料中检索并回答。',
  })
  // 思维导图等页面跳转过来时预填问题
  const q = route.query.q
  if (typeof q === 'string' && q.trim()) {
    input.value = q.trim()
  }
})
</script>

<template>
  <div class="chat-page">
    <div class="chat-header">
      <h2>AI 问答</h2>
      <p class="subtitle">基于你上传的资料（RAG）：检索相关切片 → 生成答案，并附上引用来源。</p>
    </div>

    <div class="chat-container">
      <div ref="scrollRef" class="chat-messages">
        <div v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="msg.role">
          <div class="msg-bubble">
            <template v-if="msg.loading">
              <span class="dot-flashing" />
            </template>
            <template v-else>
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
  </div>
</template>

<style scoped lang="scss">
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
}
.chat-header {
  margin-bottom: 12px;
  h2 { margin: 0; }
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
  border: 1px solid #ebeef5;
  border-radius: 12px;
  background: #fff;
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
