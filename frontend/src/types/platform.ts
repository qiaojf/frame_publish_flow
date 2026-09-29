export type CapabilityFieldType = 'text' | 'textarea' | 'tags' | 'boolean' | 'select' | 'number'

export interface PlatformCapabilityField {
  key: string
  label: string
  type: CapabilityFieldType
  required?: boolean
  placeholder?: string
  options?: Array<{ label: string; value: string } | string>
  max_length?: number
  default?: string | number | boolean | string[]
}

export interface PublishAccount {
  id: string
  platform_id: string
  name: string
  account_identifier?: string
  ig_user_id?: string
  enabled: boolean
  client_id_masked?: string
  client_secret_masked?: string
  access_token_masked?: string
  refresh_token_masked?: string
  token_expires_at?: string
  authorized_scopes?: string[]
  extra_config?: Record<string, unknown>
}

export interface PublishPlatform {
  id: string
  name: string
  code: string
  description?: string
  adapter_type?: string
  api_base_url?: string
  enabled: boolean
  capabilities: {
    fields?: PlatformCapabilityField[]
    supports_cover?: boolean
    [key: string]: unknown
  }
  accounts?: PublishAccount[]
}

export interface PublishPlatformInput extends Omit<PublishPlatform, 'id' | 'accounts'> {}

export interface PublishAccountInput {
  platform_id: string
  name: string
  account_identifier?: string
  ig_user_id?: string
  enabled: boolean
  client_id?: string
  client_secret?: string
  access_token?: string
  refresh_token?: string
  token_expires_at?: string
  authorized_scopes?: string[]
  extra_config?: Record<string, unknown>
}
