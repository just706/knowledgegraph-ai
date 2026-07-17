import axios, { type AxiosInstance, type AxiosResponse } from 'axios'
import { showToast } from 'vant'
import { API_BASE_URL } from '@/constants/api'
import { useAuthStore } from '@/store/auth'

const request: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const token = useAuthStore().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    showToast({ message, position: 'bottom' })
    return Promise.reject(error)
  },
)

export default request
