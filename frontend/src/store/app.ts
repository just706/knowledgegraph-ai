import { defineStore } from 'pinia'

// 全局应用状态占位（Phase 2 用户系统接入时扩展 auth 状态）
export const useAppStore = defineStore('app', {
  state: () => ({
    appName: 'KnowledgeGraph AI',
  }),
})
