import request from '@/utils/request'

export interface MistakeItem {
  id: number
  question: string
  my_answer: string
  correct_answer: string
  error_reason: string | null
  subject: string | null
  mastered: boolean
  review_count: number
  review_stage: number
  next_review_at: string | null
  last_review_at: string | null
  created_at: string
}

export interface MistakeCreate {
  question: string
  my_answer: string
  correct_answer: string
  error_reason?: string
  subject?: string
}

export function listMistakes(params?: { mastered?: boolean; subject?: string }): Promise<MistakeItem[]> {
  return request.get('/mistakes', { params })
}

export function listSubjects(): Promise<string[]> {
  return request.get('/mistakes/subjects')
}

export function createMistake(data: MistakeCreate): Promise<MistakeItem> {
  return request.post('/mistakes', data)
}

export function reviewMistake(id: number, action: 'schedule' | 'confirm'): Promise<MistakeItem> {
  return request.post(`/mistakes/${id}/review`, { action })
}

export function explainMistake(id: number): Promise<{
  mistake_id: number
  explanation: string
  error_type: string | null
  suggestion: string | null
}> {
  return request.post(`/mistakes/${id}/explain`)
}

export function analyzeWeakness(): Promise<{
  weak_subjects: string[]
  suggestions: string[]
}> {
  return request.post('/mistakes/analyze-weakness')
}

export function deleteMistake(id: number): Promise<void> {
  return request.delete(`/mistakes/${id}`)
}
