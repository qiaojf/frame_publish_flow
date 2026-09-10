import { apiGet, apiPost } from '@/utils/request'
import type { PageResult, QueryParams } from '@/types/common'
import type { PublishTask, PublishTaskBatch, PublishTaskInput } from '@/types/publish'

export async function createPublishTasks(payload: PublishTaskInput) {
  const form = new FormData()
  const { cover, ...body } = payload
  form.append('payload', JSON.stringify(body))
  if (cover) form.append('cover', cover)
  return apiPost<PublishTaskBatch>('/publish/tasks', form, {
    headers: { 'Idempotency-Key': crypto.randomUUID() },
  })
}

export const getPublishTasks = (params?: QueryParams) => apiGet<PageResult<PublishTask>>('/publish/tasks', { params })
export const getPublishTask = (id: string) => apiGet<PublishTask>(`/publish/tasks/${id}`)
export const retryPublishTask = (id: string) => apiPost<PublishTask>(`/publish/tasks/${id}/retry`)
