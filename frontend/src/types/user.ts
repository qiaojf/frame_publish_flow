export type UserRole = 'admin' | 'user'
import type { SupportedLocale } from '@/locales'

export interface User {
  id: string
  username: string
  display_name?: string
  email?: string
  role: UserRole
  preferred_locale: SupportedLocale
  enabled: boolean
  created_at?: string
  last_login_at?: string
}

export interface UserInput {
  username: string
  display_name?: string
  email?: string
  role: UserRole
  enabled: boolean
  password?: string
  preferred_locale?: SupportedLocale
}
