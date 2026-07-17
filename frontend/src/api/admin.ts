import request from '@/utils/request'

export interface AdminUserSummary {
  id: number
  email: string
  display_name: string | null
  is_active: boolean
  role: string
  created_at: string | null
  document_count: number
  chat_session_count: number
  entity_count: number
  mistake_count: number
  quiz_count: number
}

export interface SystemStats {
  total_users: number
  active_users: number
  admin_users: number
  total_documents: number
  total_chunks: number
  total_chat_sessions: number
  total_chat_messages: number
  total_entities: number
  total_relations: number
  total_mistakes: number
  total_quizzes: number
}

export interface AdminDashboard {
  stats: SystemStats
  recent_users: AdminUserSummary[]
}

export function getDashboard(): Promise<AdminDashboard> {
  return request.get('/admin/dashboard')
}

export function listUsers(params?: {
  q?: string
  role?: string
  active_only?: boolean
  offset?: number
  limit?: number
}): Promise<AdminUserSummary[]> {
  return request.get('/admin/users', { params })
}

export function getUserDetail(userId: number): Promise<AdminUserSummary> {
  return request.get(`/admin/users/${userId}`)
}

export function toggleUserActive(userId: number, isActive: boolean): Promise<AdminUserSummary> {
  return request.put(`/admin/users/${userId}/active`, { is_active: isActive })
}

export function setUserRole(userId: number, role: string): Promise<AdminUserSummary> {
  return request.put(`/admin/users/${userId}/role`, { role })
}
