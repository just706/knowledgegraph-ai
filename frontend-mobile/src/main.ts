import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from '@/store/auth'
import 'vant/lib/index.css'
import './styles/global.scss'
import './styles/markdown.scss'

// 全局错误兜底：把运行期错误显示在页面上，便于在手机端直接看到“打不开”的真正原因。
function showFatal(msg: string) {
  const el = document.getElementById('fatal')
  if (!el) {
    const d = document.createElement('div')
    d.id = 'fatal'
    d.style.cssText =
      'position:fixed;left:0;right:0;top:0;z-index:9999;background:#fff3f3;color:#d00;' +
      'font-size:13px;padding:12px 16px;white-space:pre-wrap;word-break:break-all;border-bottom:1px solid #faa'
    document.body.appendChild(d)
    d.textContent = '页面错误：\n' + msg
  } else {
    el.textContent += '\n' + msg
  }
}
window.addEventListener('error', (e) => showFatal((e as ErrorEvent).message || String(e)))
window.addEventListener('unhandledrejection', (e) =>
  showFatal('Promise: ' + ((e as PromiseRejectionEvent).reason?.toString?.() || String(e))),
)

const app = createApp(App)
app.use(createPinia())
app.use(router)

// 先挂载，保证页面（含登录页）立即可交互，避免 top-level await 在弱网/
// 体验登录异常时阻塞整个应用导致“白屏/点不动”。
// 会话在 App.vue 内异步 ensureSession 完成后，由路由守卫/状态监听自动跳转。
const auth = useAuthStore()
void auth
  .ensureSession()
  .catch((err) => showFatal('ensureSession: ' + (err?.message || err)))

app.mount('#app')
