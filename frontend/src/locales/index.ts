import { createI18n } from 'vue-i18n'
import zhCN from './zh-CN'
import jaJP from './ja-JP'
import enUS from './en-US'

export const supportedLocales = ['zh-CN', 'ja-JP', 'en-US'] as const
export type SupportedLocale = (typeof supportedLocales)[number]

export const localeStorageKey = 'frameflow_locale'
const configuredDefault = import.meta.env.VITE_DEFAULT_LOCALE
export const defaultLocale: SupportedLocale = isSupportedLocale(configuredDefault) ? configuredDefault : 'zh-CN'

export function isSupportedLocale(value: unknown): value is SupportedLocale {
  return typeof value === 'string' && supportedLocales.includes(value as SupportedLocale)
}

export function normalizeLocale(value?: string | null): SupportedLocale | undefined {
  const normalized = value?.trim().toLowerCase()
  if (!normalized) return undefined
  if (normalized.startsWith('zh')) return 'zh-CN'
  if (normalized.startsWith('ja')) return 'ja-JP'
  if (normalized.startsWith('en')) return 'en-US'
  return undefined
}

export function detectInitialLocale(): SupportedLocale {
  const stored = localStorage.getItem(localeStorageKey)
  return normalizeLocale(stored) ?? normalizeLocale(navigator.language) ?? defaultLocale
}

export const i18n = createI18n({
  legacy: false,
  locale: detectInitialLocale(),
  fallbackLocale: 'en-US',
  messages: { 'zh-CN': zhCN, 'ja-JP': jaJP, 'en-US': enUS },
  missingWarn: import.meta.env.DEV,
  fallbackWarn: import.meta.env.DEV,
})

export function getCurrentLocale(): SupportedLocale {
  const current = i18n.global.locale.value
  return isSupportedLocale(current) ? current : defaultLocale
}

export function setLocale(locale: SupportedLocale, persist = true): void {
  i18n.global.locale.value = locale
  document.documentElement.lang = locale
  if (persist) localStorage.setItem(localeStorageKey, locale)
}

document.documentElement.lang = getCurrentLocale()
