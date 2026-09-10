import { apiDelete, apiGet, apiPatch, apiPost } from '@/utils/request'
import type { PageResult, QueryParams } from '@/types/common'
import type { PublishAccount, PublishAccountInput, PublishPlatform, PublishPlatformInput } from '@/types/platform'

export const getPublishPlatforms = () => apiGet<PublishPlatform[]>('/publish/platforms')
export const getAdminPlatforms = (params?: QueryParams) => apiGet<PageResult<PublishPlatform>>('/admin/platforms', { params })
export const getAdminPlatform = (id: string) => apiGet<PublishPlatform>(`/admin/platforms/${id}`)
export const createPlatform = (payload: PublishPlatformInput) => apiPost<PublishPlatform>('/admin/platforms', payload)
export const updatePlatform = (id: string, payload: Partial<PublishPlatformInput>) =>
  apiPatch<PublishPlatform>(`/admin/platforms/${id}`, payload)
export const deletePlatform = (id: string) => apiDelete<void>(`/admin/platforms/${id}`)

export const getAccounts = (params?: QueryParams) => apiGet<PageResult<PublishAccount>>('/admin/accounts', { params })
export const createAccount = (payload: PublishAccountInput) => apiPost<PublishAccount>('/admin/accounts', payload)
export const updateAccount = (id: string, payload: Partial<PublishAccountInput>) =>
  apiPatch<PublishAccount>(`/admin/accounts/${id}`, payload)
export const deleteAccount = (id: string) => apiDelete<void>(`/admin/accounts/${id}`)
