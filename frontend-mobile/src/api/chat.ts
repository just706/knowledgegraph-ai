import request from '@/utils/request'

export interface ChatSource {
  document_id: number
  chunk_index: number
  snippet: string
  score: number
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
  sources: ChatSource[]
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
  session_id?: number
}

export function sendChat(payload: AskPayload): Promise<{
  session_id: number
  session_title: string
  answer: string
  sources: ChatSource[]
  mode: 'llm' | 'local'
}> {
  return request.post('/chat/', payload)
}

export function listSessions(): Promise<ChatSession[]> {
  return request.get('/chat/sessions')
}

export function createSession(): Promise<ChatSession> {
  return request.post('/chat/sessions')
}

export function getSessionMessages(sessionId: number, page = 1, pageSize = 50): Promise<Paginated<ChatMessage>> {
  return request.get(`/chat/sessions/${sessionId}`, { params: { page, page_size: pageSize } })
}

export function deleteSession(sessionId: number): Promise<void> {
  return request.delete(`/chat/sessions/${sessionId}`)
}
