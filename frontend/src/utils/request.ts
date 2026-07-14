import axios, { type AxiosInstance, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { API_BASE_URL } from '@/constants/api'

// 统一请求封装：异步任务必须提供状态反馈（AI 宪法第六章）
const request: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

request.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default request
