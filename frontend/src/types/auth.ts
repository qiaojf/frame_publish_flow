import type { User } from './user'

export interface LoginPayload {
  username: string
  password: string
}

export interface LoginResponse {
  access_token?: string
  token?: string
  token_type?: string
  user?: User
}
