import request from '@/utils/request'

export type QuizSource = 'knowledge' | 'mistakes' | 'graph'
export type QuizType = 'choice' | 'fill' | 'judgment' | 'short'

export interface QuizItem {
  id: number
  source: QuizSource
  q_type: QuizType
  question: string
  options: string[] | null
  answer: string
  explanation: string | null
  difficulty: number | null
  knowledge_point: string | null
}

export interface GenerateRequest {
  source: QuizSource
  q_types?: QuizType[]
  count?: number
  category?: string
}

export function generateQuizzes(data: GenerateRequest): Promise<QuizItem[]> {
  return request.post('/quiz/generate', data)
}

export interface SubmitPayload {
  session_id?: number
  answers: Array<{
    quiz_id: number
    user_answer: string
  }>
}

export interface SubmitResult {
  total: number
  correct: number
  score: number
  details: Array<{
    quiz_id: number
    question: string
    user_answer: string
    correct_answer: string
    is_correct: boolean
    explanation: string | null
    advanced_mistake_ids: number[]
  }>
}

export function submitQuiz(data: SubmitPayload): Promise<SubmitResult> {
  return request.post('/quiz/grade', data)
}
