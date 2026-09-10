export type UserRole = 'admin' | 'user'

export interface User {
  id: string
  username: string
  display_name?: string
  email?: string
  role: UserRole
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
}
