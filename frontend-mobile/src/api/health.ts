import request from '@/utils/request'

export function getHealth(): Promise<{ status: string; app_name: string; version: string }> {
  return request.get('/health')
}
