import { apiGet, apiPost } from '@/utils/request'
import type { LoginPayload, LoginResponse } from '@/types/auth'
import type { User } from '@/types/user'

export const login = (payload: LoginPayload) => apiPost<LoginResponse>('/auth/login', payload)
export const getCurrentUser = () => apiGet<User>('/auth/me')
