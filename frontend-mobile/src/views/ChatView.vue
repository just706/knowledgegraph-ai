<template>
  <div class="chat-view">
    <van-nav-bar title="AI助手" :right-text="sessionListVisible ? '完成' : '会话'" @click-right="toggleSessionList" />

    <!-- 会话列表 -->
    <div v-if="sessionListVisible" class="session-list">
      <van-cell
        v-for="s in sessions"
        :key="s.id"
        :title="s.title || '新会话'"
        :label="s.updated_at"
        is-link
        @click="selectSession(s.id)"
      >
        <template #right-icon>
          <van-icon name="delete-o" class="delete-icon" @click.stop="deleteSession(s.id)" />
        </template>
      </van-cell>
      <van-empty v-if="sessions.length === 0" description="暂无会话" />
    </div>

    <!-- 聊天区 -->
    <div v-else class="chat-area">
      <div class="messages" ref="messagesEl">
        <van-empty
          v-if="messages.length === 0 && !sending"
          image="search"
          description="问我任何学习问题，我会结合你的资料回答"
        />
        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="msg"
          :class="msg.role"
        >
          <div class="avatar" :class="msg.role">
            {{ msg.role === 'user' ? '我' : 'AI' }}
          </div>
          <div class="msg-body">
            <div
              class="bubble"
              :class="{ 'md-body': msg.role === 'assistant' }"
              v-html="msg.role === 'assistant' ? renderMarkdown(msg.content) : msg.content"
            ></div>
            <div v-if="msg.sources?.length" class="sources">
              <span v-for="src in msg.sources" :key="src.chunk_index" class="source-tag">
                来源: {{ src.snippet.slice(0, 20) }}...
              </span>
            </div>
          </div>
        </div>
        <div v-if="sending && messages[messages.length - 1]?.role === 'user'" class="msg assistant">
          <div class="avatar assistant">AI</div>
          <div class="msg-body">
            <div class="bubble thinking">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
          </div>
        </div>
      </div>

      <div class="input-bar">
        <van-field
          v-model="query"
          placeholder="输入你的问题..."
          @keyup.enter="send"
        >
          <template #button>
            <van-button size="small" type="primary" :loading="sending" @click="send">发送</van-button>
          </template>
        </van-field>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { showToast } from 'vant'
import {
  listSessions, getSessionMessages, deleteSession as apiDeleteSession, sendChat, type ChatSession, type ChatMessage,
} from '@/api/chat'
import { renderMarkdown } from '@/utils/markdown'

const sessionListVisible = ref(false)
const sessions = ref<ChatSession[]>([])
const messages = ref<ChatMessage[]>([])
const currentSessionId = ref<number | null>(null)
const query = ref('')
const sending = ref(false)
const messagesEl = ref<HTMLElement | null>(null)

async function toggleSessionList() {
  sessionListVisible.value = !sessionListVisible.value
  if (sessionListVisible.value) {
    sessions.value = await listSessions()
  }
}

async function selectSession(id: number) {
  currentSessionId.value = id
  sessionListVisible.value = false
  const res = await getSessionMessages(id)
  messages.value = res.items
  scrollToBottom()
}

async function send() {
  if (!query.value.trim()) return
  const q = query.value
  query.value = ''
  sending.value = true

  // 乐观更新
  messages.value.push({ id: -1, session_id: 0, role: 'user', content: q, sources: [], gen_mode: null, created_at: '' } as ChatMessage)
  scrollToBottom()

  try {
    const res = await sendChat({ query: q, session_id: currentSessionId.value || undefined })
    currentSessionId.value = res.session_id
    messages.value.push({ id: -2, session_id: res.session_id, role: 'assistant', content: res.answer, sources: res.sources, gen_mode: res.mode, created_at: '' } as ChatMessage)
    scrollToBottom()
  } catch {
    // error toast in interceptor
  } finally {
    sending.value = false
  }
}

async function deleteSession(id: number) {
  await apiDeleteSession(id)
  sessions.value = await listSessions()
  showToast('已删除')
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

onMounted(async () => {
  sessions.value = await listSessions()
})
</script>

<style scoped lang="scss">
.chat-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 50px);
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.delete-icon {
  font-size: 18px;
  color: var(--kg-text-secondary);
  margin-left: 8px;
}

.chat-area {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.msg {
  margin-bottom: 16px;
  display: flex;
  align-items: flex-start;
  gap: 8px;

  &.user {
    flex-direction: row-reverse;
    .bubble {
      background: var(--kg-primary);
      color: #fff;
    }
  }

  &.assistant {
    .bubble {
      background: var(--kg-card);
    }
  }
}

.avatar {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #fff;

  &.user {
    background: var(--kg-primary);
  }
  &.assistant {
    background: #07c160;
  }
}

.msg-body {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.bubble {
  max-width: 75vw;
  padding: 10px 14px;
  border-radius: 12px;
  word-break: break-word;
  line-height: 1.6;

  &.thinking {
    display: flex;
    gap: 5px;
    padding: 14px;

    .dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--kg-text-secondary);
      animation: blink 1.2s infinite ease-in-out both;

      &:nth-child(2) { animation-delay: 0.2s; }
      &:nth-child(3) { animation-delay: 0.4s; }
    }
  }
}

@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

.sources {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.source-tag {
  font-size: 11px;
  color: var(--kg-text-secondary);
  background: var(--kg-bg);
  padding: 2px 6px;
  border-radius: 4px;
}

.input-bar {
  border-top: 1px solid var(--kg-border);
  background: var(--kg-card);
}
</style>
