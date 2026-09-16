import axios from 'axios'

interface ErrorPayload {
  message?: string
  detail?: string | Array<{ msg?: string }>
}

export function getErrorMessage(error: unknown, fallback = '请求失败，请稍后重试'): string {
  if (axios.isAxiosError<ErrorPayload>(error)) {
    const data = error.response?.data
    if (data?.message) return data.message
    if (typeof data?.detail === 'string') return data.detail
    if (Array.isArray(data?.detail)) {
      const messages = data.detail.map((item) => item.msg).filter(Boolean)
      if (messages.length) return messages.join('；')
    }
    if (error.code === 'ECONNABORTED') return '请求超时，请检查服务状态后重试'
    if (!error.response) return '网络连接失败，请确认后端服务已启动'
    if (error.response.status === 413) return '上传文件过大，请选择不超过 10 MB 的图片'
    return error.message || fallback
  }
  return error instanceof Error ? error.message : fallback
}
