import request from '@/utils/request'

export interface ChatSource {
  document_id: number
  chunk_index: number
  snippet: string
  score: number
}

export interface ChatResponse {
  answer: string
  sources: ChatSource[]
}

export function askQuestion(query: string, topK: number = 5): Promise<ChatResponse> {
  return request.post('/chat', { query, top_k: topK })
}
