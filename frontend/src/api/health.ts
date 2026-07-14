import request from '@/utils/request'

export interface HealthCheck {
  status: string
  app_name: string
  version: string
}

export function getHealth(): Promise<HealthCheck> {
  return request.get('/health')
}
