export interface OperationLog {
  id: string
  user_id?: string
  username?: string
  action: string
  resource_type: string
  resource_id?: string
  result: 'success' | 'failed'
  ip_address?: string
  error_message?: string
  created_at: string
}
