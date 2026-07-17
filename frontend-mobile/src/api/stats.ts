import request from '@/utils/request'

export interface StatsOverview {
  total_documents: number
  total_entities: number
  total_relations: number
  total_mistakes: number
  mastered_mistakes: number
  unmastered_mistakes: number
  total_quiz_sessions: number
  total_quiz_questions: number
  avg_score: number
  recent_trend: Array<{ date: string; count: number }>
  knowledge_points: Array<{ name: string; mastery: number }>
  ability_radar: Array<{ subject: string; score: number }>
  suggestions: string[]
}

export function getOverview(): Promise<StatsOverview> {
  return request.get('/stats/overview')
}
