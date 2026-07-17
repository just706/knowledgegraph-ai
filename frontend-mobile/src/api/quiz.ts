import request from '@/utils/request'

export type QuizSource = 'knowledge' | 'mistakes' | 'graph'
export type QuizType = 'choice' | 'fill' | 'judgment' | 'short'

/** 单道题目（与后端 QuizQuestion 对齐） */
export interface QuizItem {
  source: string
  q_type: QuizType
  subject: string
  question: string
  options: string[]
  answer: string
  explanation: string
  difficulty: number
  knowledge_point: string
}

export interface GenerateRequest {
  sources: QuizSource[]
  count?: number
  subject?: string
  q_types?: QuizType[]
}

export interface GenerateResponse {
  questions: QuizItem[]
  mode: string
  message: string
}

export function generateQuizzes(data: GenerateRequest): Promise<GenerateResponse> {
  return request.post('/quiz/generate', data)
}

/** 提交作答的一条记录（与后端 QuizAnswerItem 对齐） */
export interface QuizAnswerItem {
  question: string
  user_answer: string
  answer: string
  source?: string
  subject?: string
  explanation?: string
  q_type?: QuizType
}

export interface SubmitPayload {
  answers: QuizAnswerItem[]
}

export interface SubmitDetail {
  question: string
  user_answer: string
  correct_answer: string
  is_correct: boolean
  explanation: string | null
  advanced_mistake_ids: number[]
}

export interface SubmitResult {
  total: number
  correct: number
  wrong: number
  score: number
  wrong_items: QuizAnswerItem[]
  advanced_mistake_ids: number[]
  details: SubmitDetail[]
}

export function submitQuiz(data: SubmitPayload): Promise<SubmitResult> {
  return request.post('/quiz/grade', data)
}
