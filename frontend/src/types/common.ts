export interface ApiEnvelope<T> {
  success: boolean
  data: T
  message?: string | null
  error_code?: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export type GenerationTaskStatus = 'pending' | 'processing' | 'success' | 'failed' | 'cancelled' | 'timeout'
export type PublishTaskStatus = 'pending' | 'publishing' | 'success' | 'failed' | 'cancelled'
export type TaskStatus = GenerationTaskStatus | PublishTaskStatus

export interface QueryParams {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  [key: string]: string | number | boolean | undefined
}
