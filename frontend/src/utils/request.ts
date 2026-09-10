import axios, { type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiEnvelope } from '@/types/common'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
const timeout = Number(import.meta.env.VITE_REQUEST_TIMEOUT_MS ?? 20_000)
const tokenKey = 'frameflow_token'

export const request = axios.create({ baseURL, timeout })

request.interceptors.request.use((config) => {
  const token = localStorage.getItem(tokenKey)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

request.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      if (error.response?.status === 401) {
        localStorage.removeItem(tokenKey)
        if (window.location.pathname !== '/login') {
          ElMessage.error('登录已过期，请重新登录')
          const redirect = encodeURIComponent(`${window.location.pathname}${window.location.search}`)
          window.location.assign(`/login?redirect=${redirect}`)
        }
      } else if (error.response?.status === 403) {
        ElMessage.warning('当前账号无权执行此操作')
      }
    }
    return Promise.reject(error)
  },
)

function unwrap<T>(payload: ApiEnvelope<T> | T): T {
  if (payload && typeof payload === 'object' && 'success' in payload && 'data' in payload) {
    const envelope = payload as ApiEnvelope<T>
    if (!envelope.success) throw new Error(envelope.message || '业务请求失败')
    return envelope.data
  }
  return payload as T
}

export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await request.get<ApiEnvelope<T> | T>(url, config)
  return unwrap(response.data)
}

export async function apiPost<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const response = await request.post<ApiEnvelope<T> | T>(url, data, config)
  return unwrap(response.data)
}

export async function apiPatch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const response = await request.patch<ApiEnvelope<T> | T>(url, data, config)
  return unwrap(response.data)
}

export async function apiDelete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await request.delete<ApiEnvelope<T> | T>(url, config)
  return unwrap(response.data)
}

export { tokenKey }
