import { apiDelete, apiGet, apiPatch, apiPost } from '@/utils/request'
import type { PageResult, QueryParams } from '@/types/common'
import type { VideoModelInput, VideoModelOption } from '@/types/video-model'

export const getVideoModels = () => apiGet<VideoModelOption[]>('/video-models')
export const getAdminVideoModels = (params?: QueryParams) =>
  apiGet<PageResult<VideoModelOption>>('/admin/video-models', { params })
export const getAdminVideoModel = (id: string) => apiGet<VideoModelOption>(`/admin/video-models/${id}`)
export const createVideoModel = (payload: VideoModelInput) => apiPost<VideoModelOption>('/admin/video-models', payload)
export const updateVideoModel = (id: string, payload: Partial<VideoModelInput>) =>
  apiPatch<VideoModelOption>(`/admin/video-models/${id}`, payload)
export const deleteVideoModel = (id: string) => apiDelete<void>(`/admin/video-models/${id}`)
