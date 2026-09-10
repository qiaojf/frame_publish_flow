import type { PublishTaskStatus } from './common'

export interface PublishTargetInput {
  platform_id: string
  account_id: string
  overrides?: Record<string, unknown>
}

export interface PublishTaskInput {
  video_id: string
  title: string
  description?: string
  tags?: string[]
  targets: PublishTargetInput[]
  cover?: File
}

export interface PublishTask {
  id: string
  video_id: string
  video_title?: string
  video_thumbnail_url?: string
  platform_id: string
  platform_name: string
  account_id?: string
  account_name?: string
  status: PublishTaskStatus
  published_at?: string
  created_at: string
  publish_url?: string
  error_message?: string
}

export interface PublishTaskBatch {
  tasks: PublishTask[]
}
