import request from '@/utils/request'

export interface AdminUserSummary {
  id: number
  email: string
  display_name: string | null
  role: string
  is_active: boolean
  created_at: string
}

export interface AdminDashboard {
  total_users: number
  active_users: number
  total_documents: number
  total_mistakes: number
  system_stats: {
    cpu_percent: number
    memory_percent: number
    disk_percent: number
  }
}

export function getDashboard(): Promise<AdminDashboard> {
  return request.get('/admin/dashboard')
}

export function listUsers(params?: { search?: string; skip?: number; limit?: number }): Promise<AdminUserSummary[]> {
  return request.get('/admin/users', { params })
}

export function updateUser(id: number, data: { is_active?: boolean; role?: string }): Promise<void> {
  return request.put(`/admin/users/${id}`, data)
}
