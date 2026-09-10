import { apiGet, apiPost } from '@/utils/request'
import type { PageResult, QueryParams } from '@/types/common'
import type { GenerationTask, GenerationTaskInput } from '@/types/generation'

export async function createGenerationTask(payload: GenerationTaskInput) {
  const form = new FormData()
  form.append('prompt', payload.prompt)
  form.append('model_id', payload.model_id)
  if (payload.duration !== undefined) form.append('duration', String(payload.duration))
  if (payload.aspect_ratio) form.append('aspect_ratio', payload.aspect_ratio)
  if (payload.resolution) form.append('resolution', payload.resolution)
  if (payload.image) form.append('image', payload.image)
  return apiPost<GenerationTask>('/generation/tasks', form)
}

export const getGenerationTask = (id: string) => apiGet<GenerationTask>(`/generation/tasks/${id}`)
export const getGenerationTasks = (params?: QueryParams) =>
  apiGet<PageResult<GenerationTask>>('/generation/tasks', { params })
