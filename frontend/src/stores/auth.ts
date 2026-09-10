import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { login as loginRequest, getCurrentUser } from '@/api/auth'
import type { LoginPayload } from '@/types/auth'
import type { User } from '@/types/user'
import { tokenKey } from '@/utils/request'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(tokenKey) ?? '')
  const user = ref<User | null>(null)
  const initialized = ref(false)
  const isAuthenticated = computed(() => Boolean(token.value))
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(payload: LoginPayload) {
    const result = await loginRequest(payload)
    const accessToken = result.access_token ?? result.token
    if (!accessToken) throw new Error('登录响应中缺少访问令牌')
    token.value = accessToken
    localStorage.setItem(tokenKey, accessToken)
    user.value = result.user ?? (await getCurrentUser())
    initialized.value = true
  }

  async function fetchCurrentUser() {
    if (!token.value) {
      initialized.value = true
      return null
    }
    try {
      user.value = await getCurrentUser()
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

  return { token, user, initialized, isAuthenticated, isAdmin, login, fetchCurrentUser, logout }
})
