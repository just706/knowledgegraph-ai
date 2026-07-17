import request from '@/utils/request'

export interface CountItem {
  name: string
  count: number
}

export interface MasteryItem {
  name: string
  value: number // 掌握度 0-100
  total: number
  correct: number
}

export interface TrendItem {
  date: string
  count: number
}

export interface StatsOverview {
  // 概览卡片
  document_count: number
  chunk_count: number
  entity_count: number
  relation_count: number
  mistake_total: number
  mistake_mastered: number
  mastery_rate: number // 0-100

  // 分布/趋势图
  entity_label_dist: CountItem[]
  mistake_subject_dist: CountItem[]
  mistake_trend_7d: TrendItem[]

  // 学习中心增强字段
  quiz_total: number
  knowledge_mastery: MasteryItem[]
  mastered_entity_count: number
  study_hours: number
  ability_radar: CountItem[]
  recent_documents: Array<{ title: string; created_at?: string }>
  recent_mistakes: Array<{ question: string; subject?: string }>
  ai_suggestion: string
  today_goal: string
}

export function getOverview(): Promise<StatsOverview> {
  return request.get('/stats/overview')
}
