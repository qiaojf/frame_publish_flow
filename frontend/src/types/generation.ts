import type { GenerationTaskStatus } from './common'

export interface GenerationTask {
  id: string
  status: GenerationTaskStatus
  prompt: string
  model_id: string
  model_name?: string
  generation_type?: 'text_to_video' | 'image_to_video'
  error_code?: string
  error_message?: string
  video_id?: string
  created_at: string
  completed_at?: string
}

export interface GenerationTaskInput {
  prompt: string
  model_id: string
  duration?: number
  aspect_ratio?: string
  resolution?: string
  image?: File
}
