import { apiDelete, apiGet, request } from '@/utils/request'
import type { PageResult, QueryParams } from '@/types/common'
import type { VideoAsset } from '@/types/video'

export const getVideos = (params?: QueryParams) => apiGet<PageResult<VideoAsset>>('/videos', { params })
export const getVideo = (id: string) => apiGet<VideoAsset>(`/videos/${id}`)
export const deleteVideo = (id: string) => apiDelete<void>(`/videos/${id}`)
export const downloadVideo = (id: string) => request.get<Blob>(`/videos/${id}/download`, { responseType: 'blob' })
