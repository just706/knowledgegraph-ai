import request from '@/utils/request'

export interface ChatSource {
  document_id: number
  chunk_index: number
  snippet: string
  score: number
}

export interface ChatResponse {
  session_id: number
  session_title: string
  answer: string
  sources: ChatSource[]
  // 生成模式：llm（AI 生成）/ local（本地模式）
  mode: 'llm' | 'local'
}

export type ChatMode = 'normal' | 'beginner' | 'exam' | 'interview'

export interface ChatSession {
  id: number
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  session_id: number
  role: 'user' | 'assistant'
  content: string
  sources: Record<string, unknown>[]
  gen_mode: 'llm' | 'local' | null
  created_at: string
}

export interface Paginated<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

export interface AskPayload {
  query: string
  top_k?: number
  mode?: ChatMode
  session_id?: number | null
}

export function askQuestion(payload: AskPayload): Promise<ChatResponse> {
  return request.post('/chat', {
    query: payload.query,
    top_k: payload.top_k ?? 5,
    mode: payload.mode ?? 'normal',
    session_id: payload.session_id ?? null,
  })
}

export function listSessions(page = 1, pageSize = 20): Promise<Paginated<ChatSession>> {
  return request.get('/chat/sessions', { params: { page, page_size: pageSize } })
}

export function createSession(title?: string): Promise<ChatSession> {
  return request.post('/chat/sessions', { title: title ?? null })
}

export function getSessionMessages(
  sessionId: number,
  page = 1,
  pageSize = 50,
): Promise<Paginated<ChatMessage>> {
  return request.get(`/chat/sessions/${sessionId}`, {
    params: { page, page_size: pageSize },
  })
}

export function deleteSession(sessionId: number): Promise<void> {
  return request.delete(`/chat/sessions/${sessionId}`)
}
