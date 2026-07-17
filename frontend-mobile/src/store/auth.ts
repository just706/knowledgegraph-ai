import { defineStore } from 'pinia'
import { getCurrentUser, loginUser, registerUser, type UserPublic } from '@/api/user'

const TOKEN_KEY = 'kg_ai_mobile_token'

// 体验账户：用户打开应用即自动以此账户登录，无需手动注册/登录即可体验全部功能。
// 个人中心可看到账户信息；如需使用自己的资料，可在登录页手动登录自己的账号。
const DEMO_EMAIL = '1234567@qq.com'
const DEMO_PASSWORD = 'admin'

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
    isLoggedIn: (state) => !!state.token && !!state.user,
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
    /**
     * 保证有可用会话：用户打开应用即可体验。
     * - 已有合法会话（token + user）直接返回；
     * - 仅有 token（如刷新后），尝试拉取用户信息，失败则降级为体验账户；
     * - 完全未登录，则以体验账户静默登录（无 toast，失败也不影响页面展示）。
     */
    async ensureSession() {
      if (this.isLoggedIn) return
      if (this.token) {
        try {
          await this.fetchUser()
          if (this.user) return
        } catch {
          // token 失效，继续走体验登录
        }
      }
      try {
        await this.login(DEMO_EMAIL, DEMO_PASSWORD)
      } catch {
        // 体验登录失败（如网络/后端不可用），保持未登录态，页面仍可浏览
      }
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
