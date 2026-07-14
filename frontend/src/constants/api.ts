// API 基础地址：开发环境通过 Vite 代理走 /api，生产环境可配置 VITE_API_BASE_URL
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || '/api'
