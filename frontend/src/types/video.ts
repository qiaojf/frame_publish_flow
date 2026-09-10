import type { GenerationTaskStatus, PublishTaskStatus } from './common'

export interface VideoAsset {
  id: string
  title: string
  prompt: string
  thumbnail_url?: string
  video_url?: string
  reference_image_url?: string
  generation_type: 'text_to_video' | 'image_to_video'
  model_id?: string
  model_name: string
  duration?: number
  resolution?: string
  aspect_ratio?: string
  width?: number
  height?: number
  file_size?: number
  generation_status?: GenerationTaskStatus
  publish_status?: PublishTaskStatus | 'not_published' | 'partially_failed'
  created_at: string
}
