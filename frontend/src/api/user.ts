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

export interface ProviderPreset {
  id: string
  name: string
  kind: string
  base_url: string
  model: string
  doc: string
}

export interface LLMSettingsView {
  has_own_key: boolean
  provider: string | null
  api_key_masked: string | null
  base_url: string | null
  model: string | null
  effective_mode: 'own' | 'fallback' | 'none'
  provider_presets?: ProviderPreset[]
}

export interface LLMSettingsUpdate {
  provider?: string | null
  api_key?: string | null
  base_url?: string | null
  model?: string | null
}

export function getLLMSettings(): Promise<LLMSettingsView> {
  return request.get('/users/me/llm-settings')
}

export function updateLLMSettings(data: LLMSettingsUpdate): Promise<LLMSettingsView> {
  return request.put('/users/me/llm-settings', data)
}

export interface LLMTestResult {
  ok: boolean
  provider: string | null
  kind?: string
  model?: string
  error?: string
  detail: string
}

export function testLLMConnection(payload?: Partial<LLMSettingsUpdate>): Promise<LLMTestResult> {
  return request.post('/users/me/llm-test', payload ?? {})
}
