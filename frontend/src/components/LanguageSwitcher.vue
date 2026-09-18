<template>
  <el-select v-model="current" class="language-switcher" :aria-label="t('locale.label')" @change="changeLocale">
    <el-option :label="t('locale.zhCN')" value="zh-CN" />
    <el-option :label="t('locale.jaJP')" value="ja-JP" />
    <el-option :label="t('locale.enUS')" value="en-US" />
  </el-select>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { updateMyPreferences } from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import { getCurrentLocale, setLocale, type SupportedLocale } from '@/locales'

const { t, locale } = useI18n()
const auth = useAuthStore()
const current = computed({ get: () => locale.value as SupportedLocale, set: (value) => { locale.value = value } })

async function changeLocale(value: SupportedLocale) {
  setLocale(value)
  if (!auth.isAuthenticated || !auth.user) return
  auth.setPreferredLocale(value)
  try { await updateMyPreferences({ preferred_locale: value }) }
  catch { ElMessage.warning(t('locale.saveFailed')) }
}

if (current.value !== getCurrentLocale()) current.value = getCurrentLocale()
</script>

<style scoped>
.language-switcher { width: 118px; }
</style>
