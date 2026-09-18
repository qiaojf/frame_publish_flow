<template>
  <el-config-provider :locale="elementLocale">
    <RouterView />
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed, watchEffect } from 'vue'
import { RouterView } from 'vue-router'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import ja from 'element-plus/es/locale/lang/ja'
import en from 'element-plus/es/locale/lang/en'

const route = useRoute()
const { t, locale } = useI18n()
const elementLocale = computed(() => ({ 'zh-CN': zhCn, 'ja-JP': ja, 'en-US': en }[locale.value] ?? en))

watchEffect(() => {
  const key = String(route.meta.titleKey ?? 'routes.workspace')
  document.title = `${t(key)} · FrameFlow`
  document.documentElement.lang = locale.value
})
</script>
