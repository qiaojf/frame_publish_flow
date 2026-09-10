import { apiDelete, apiGet, apiPatch, apiPost } from '@/utils/request'
import type { PageResult, QueryParams } from '@/types/common'
import type { User, UserInput } from '@/types/user'

export const getUsers = (params?: QueryParams) => apiGet<PageResult<User>>('/admin/users', { params })
export const createUser = (payload: UserInput) => apiPost<User>('/admin/users', payload)
export const updateUser = (id: string, payload: Partial<UserInput>) => apiPatch<User>(`/admin/users/${id}`, payload)
export const deleteUser = (id: string) => apiDelete<void>(`/admin/users/${id}`)
export const resetUserPassword = (id: string, password: string) =>
  apiPost<void>(`/admin/users/${id}/reset-password`, { password })
