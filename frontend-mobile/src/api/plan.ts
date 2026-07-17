import request from '@/utils/request'

export interface PlanTask {
  title: string
  detail: string
  duration: number
  type: string
}

export interface StudyPlan {
  date: string
  goal: string
  tasks: PlanTask[]
  tip: string
  mode: 'llm' | 'local'
}

export function getTodayPlan(): Promise<StudyPlan> {
  return request.get('/plan/today')
}
