import request from '@/utils/request'

export interface MistakeItem {
  id: number
  user_id: number
  question: string
  my_answer: string
  correct_answer: string
  error_reason: string
  subject: string
  mastered: boolean
  review_count: number
  created_at: string
  updated_at: string
}

export interface MistakeCreate {
  question: string
  my_answer?: string
  correct_answer?: string
  error_reason?: string
  subject?: string
}

export interface MistakeUpdate {
  question?: string
  my_answer?: string
  correct_answer?: string
  error_reason?: string
  subject?: string
  mastered?: boolean
}

export interface MistakeExplain {
  explanation: string
  mode: string
}

export function listMistakes(params?: {
  unmastered?: boolean
  subject?: string
}): Promise<MistakeItem[]> {
  return request.get('/mistakes', { params })
}

export function listSubjects(): Promise<string[]> {
  return request.get('/mistakes/subjects')
}

export function createMistake(data: MistakeCreate): Promise<MistakeItem> {
  return request.post('/mistakes', data)
}

export function updateMistake(id: number, data: MistakeUpdate): Promise<MistakeItem> {
  return request.patch(`/mistakes/${id}`, data)
}

export function deleteMistake(id: number): Promise<void> {
  return request.delete(`/mistakes/${id}`)
}

export function explainMistake(id: number): Promise<MistakeExplain> {
  return request.post(`/mistakes/${id}/explain`)
}
