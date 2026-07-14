import request from '@/utils/request'

export interface UserPublic {
  id: number
  email: string
  display_name: string | null
  is_active: boolean
}

export interface Token {
  access_token: string
  token_type: string
}

export function registerUser(data: {
  email: string
  password: string
  display_name?: string
}): Promise<UserPublic> {
  return request.post('/users/register', data)
}

export function loginUser(data: { email: string; password: string }): Promise<Token> {
  return request.post('/users/login', data)
}

export function getCurrentUser(): Promise<UserPublic> {
  return request.get('/users/me')
}
