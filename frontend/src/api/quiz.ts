import request from '@/utils/request'

export type QuizSource = 'knowledge' | 'mistakes' | 'graph'
export type QuizType = 'choice' | 'fill' | 'judgment' | 'short'

export interface QuizQuestion {
  source: QuizSource
  q_type: QuizType
  subject: string
  question: string
  options: string[]
  answer: string
  explanation: string
  difficulty: number
  knowledge_point: string
}

export interface QuizGenerateRequest {
  sources?: QuizSource[]
  count?: number
  subject?: string | null
  q_types?: QuizType[]
}

export interface QuizGenerateResponse {
  questions: QuizQuestion[]
  mode: string
  message: string
}

export interface QuizAnswerItem {
  question: string
  user_answer: string
  answer: string
  source?: QuizSource
  subject?: string
  explanation?: string
}

export interface QuizSubmitRequest {
  answers: QuizAnswerItem[]
}

export interface QuizSubmitResponse {
  total: number
  correct: number
  wrong: number
  score: number
  wrong_items: QuizAnswerItem[]
}

export function generateQuiz(data: QuizGenerateRequest): Promise<QuizGenerateResponse> {
  return request.post('/quiz/generate', data)
}

export function gradeQuiz(data: QuizSubmitRequest): Promise<QuizSubmitResponse> {
  return request.post('/quiz/grade', data)
}
