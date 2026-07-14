import request from '@/utils/request'

export interface CountItem {
  name: string
  count: number
}

export interface TrendItem {
  date: string
  count: number
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
}

export function getStatsOverview(): Promise<StatsOverview> {
  return request.get('/stats/overview')
}
