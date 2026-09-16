export interface VideoModelCapabilities {
  durations?: number[]
  aspect_ratios?: string[]
  resolutions?: string[]
  resolution_duration_matrix?: Record<string, number[]>
  max_images?: number
  max_image_size_mb?: number
  prompt?: {
    required_for_text_to_video?: boolean
    required_for_image_to_video?: boolean
    max_length?: number
  }
  image?: {
    formats?: string[]
    max_size_mb_exclusive?: number
    short_edge_min_exclusive?: number
    aspect_ratio_min?: number
    aspect_ratio_max?: number
    supports_public_url?: boolean
    supports_base64_data_url?: boolean
  }
  [key: string]: unknown
}

export interface VideoModelOption {
  id: string
  name: string
  code: string
  provider?: string
  adapter_type?: string
  description?: string
  supports_text_to_video: boolean
  supports_image_to_video: boolean
  capabilities: VideoModelCapabilities
  enabled?: boolean
  api_base_url?: string
  model_id?: string
  api_key_masked?: string
  timeout_seconds?: number
  extra_config?: Record<string, unknown>
}

export interface VideoModelInput extends Omit<VideoModelOption, 'id' | 'api_key_masked'> {
  adapter_type: string
  api_key?: string
}
