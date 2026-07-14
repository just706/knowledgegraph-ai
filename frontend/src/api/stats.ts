import request from '@/utils/request'

export interface CountItem {
  name: string
  count: number
}

export interface TrendItem {
  date: string
  count: number
}

export interface MasteryItem {
  name: string
  value: number
  total: number
  correct: number
}

export interface StatsOverview {
  document_count: number
  chunk_count: number
  entity_count: number
  relation_count: number
  mistake_total: number
  mistake_mastered: number
  mastery_rate: number
  entity_label_dist: CountItem[]
  mistake_subject_dist: CountItem[]
  mistake_trend_7d: TrendItem[]
  quiz_total: number
  knowledge_mastery: MasteryItem[]
  mastered_entity_count: number
  study_hours: number
  ability_radar: CountItem[]
  recent_documents: { title: string; created_at: string }[]
  recent_mistakes: { question: string; subject: string }[]
  ai_suggestion: string
  today_goal: string
}

export function getStatsOverview(): Promise<StatsOverview> {
  return request.get('/stats/overview')
}
