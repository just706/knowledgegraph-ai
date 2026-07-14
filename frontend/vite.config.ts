import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 前端开发服务器配置。后端地址通过环境变量 VITE_API_BASE_URL 注入（AI 宪法：配置环境变量管理）。
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // 开发环境将 /api 代理到后端，避免跨域
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:8011',
        changeOrigin: true,
      },
    },
  },
})
