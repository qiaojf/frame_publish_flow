import axios from 'axios'
import { getCurrentLocale, i18n } from '@/locales'

interface ErrorPayload {
  message?: string
  error_code?: string
  detail?: string | Array<{ msg?: string }>
}

export function getBusinessErrorMessage(errorCode?: string | null, fallback?: string | null): string {
  if (errorCode) {
    const key = `errors.${errorCode}`
    const translated = i18n.global.t(key)
    if (translated !== key) return translated
  }
  if (fallback && getCurrentLocale() === 'zh-CN') return fallback
  return i18n.global.t('errors.businessFailed')
}

export function getErrorMessage(error: unknown, fallback = i18n.global.t('errors.requestFailed')): string {
  if (axios.isAxiosError<ErrorPayload>(error)) {
    const data = error.response?.data
    if (data?.error_code) {
      return getBusinessErrorMessage(data.error_code, data.message)
    }
    if (data?.message) return data.message
    if (typeof data?.detail === 'string') return data.detail
    if (Array.isArray(data?.detail)) {
      const messages = data.detail.map((item) => item.msg).filter(Boolean)
      if (messages.length) return messages.join('；')
    }
    if (error.code === 'ECONNABORTED') return i18n.global.t('errors.timeout')
    if (!error.response) return i18n.global.t('errors.network')
    if (error.response.status === 413) return i18n.global.t('errors.uploadTooLarge')
    return error.message || fallback
  }
  return error instanceof Error ? error.message : fallback
}
