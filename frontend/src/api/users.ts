import { apiDelete, apiGet, apiPatch, apiPost } from '@/utils/request'
import type { PageResult, QueryParams } from '@/types/common'
import type { User, UserInput } from '@/types/user'
import type { SupportedLocale } from '@/locales'

export const getUsers = (params?: QueryParams) => apiGet<PageResult<User>>('/admin/users', { params })
export const createUser = (payload: UserInput) => apiPost<User>('/admin/users', payload)
export const updateUser = (id: string, payload: Partial<UserInput>) => apiPatch<User>(`/admin/users/${id}`, payload)
export const deleteUser = (id: string) => apiDelete<void>(`/admin/users/${id}`)
export const resetUserPassword = (id: string, password: string) =>
  apiPost<void>(`/admin/users/${id}/reset-password`, { password })
export const updateMyPreferences = (payload: { preferred_locale: SupportedLocale }) =>
  apiPatch<User>('/users/me/preferences', payload)
