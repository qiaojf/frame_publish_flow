import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { login as loginRequest, getCurrentUser } from '@/api/auth'
import type { LoginPayload } from '@/types/auth'
import type { User } from '@/types/user'
import { tokenKey } from '@/utils/request'
import { i18n, isSupportedLocale, setLocale, type SupportedLocale } from '@/locales'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(tokenKey) ?? '')
  const user = ref<User | null>(null)
  const initialized = ref(false)
  const isAuthenticated = computed(() => Boolean(token.value))
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(payload: LoginPayload) {
    const result = await loginRequest(payload)
    const accessToken = result.access_token ?? result.token
    if (!accessToken) throw new Error(i18n.global.t('auth.tokenMissing'))
    token.value = accessToken
    localStorage.setItem(tokenKey, accessToken)
    user.value = result.user ?? (await getCurrentUser())
    if (isSupportedLocale(user.value.preferred_locale)) setLocale(user.value.preferred_locale)
    initialized.value = true
  }

  async function fetchCurrentUser() {
    if (!token.value) {
      initialized.value = true
      return null
    }
    try {
      user.value = await getCurrentUser()
      if (isSupportedLocale(user.value.preferred_locale)) setLocale(user.value.preferred_locale)
      return user.value
    } finally {
      initialized.value = true
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    initialized.value = true
    localStorage.removeItem(tokenKey)
  }

  function setPreferredLocale(locale: SupportedLocale) {
    if (user.value) user.value = { ...user.value, preferred_locale: locale }
  }

  return { token, user, initialized, isAuthenticated, isAdmin, login, fetchCurrentUser, logout, setPreferredLocale }
})
