import { defineStore } from 'pinia'
import { getCurrentUser, loginUser, registerUser, type UserPublic } from '@/api/user'

const TOKEN_KEY = 'kg_ai_mobile_token'

interface AuthState {
  token: string
  user: UserPublic | null
}

function loadToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: loadToken(),
    user: null,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    setToken(token: string) {
      this.token = token
      localStorage.setItem(TOKEN_KEY, token)
    },
    async login(email: string, password: string) {
      const { access_token } = await loginUser({ email, password })
      this.setToken(access_token)
      await this.fetchUser()
    },
    async register(email: string, password: string, displayName?: string) {
      await registerUser({ email, password, display_name: displayName })
      await this.login(email, password)
    },
    async fetchUser() {
      this.user = await getCurrentUser()
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
