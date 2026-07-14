import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 前端开发服务器配置。后端地址通过环境变量 VITE_API_BASE_URL 注入（AI 宪法：配置环境变量管理）。
// base：GitHub Pages 项目站点部署在 /<repo>/ 子路径下，通过 VITE_BASE 注入（默认 '/'）。
export default defineConfig({
  base: process.env.VITE_BASE || '/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // 关闭 HMR 错误覆盖层：编译错误只走 console，避免旧错误遮罩卡住整个页面导致"点不了"
    hmr: { overlay: false },
    proxy: {
      // 开发环境将 /api 代理到后端，避免跨域
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:8011',
        changeOrigin: true,
      },
    },
  },
})
