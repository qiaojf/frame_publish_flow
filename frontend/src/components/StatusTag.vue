<template>
  <el-tag :type="presentation.type" :effect="['processing', 'publishing'].includes(status) ? 'dark' : 'light'" round>
    <span class="status-dot" :class="`is-${status}`" />{{ presentation.label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { TagProps } from 'element-plus'

const props = defineProps<{ status?: string }>()
const { t } = useI18n()
const map: Record<string, TagProps['type']> = {
  pending: 'info', processing: 'primary', publishing: 'primary', success: 'success', failed: 'danger',
  cancelled: 'info', timeout: 'warning', not_published: 'info', partially_failed: 'warning', enabled: 'success', disabled: 'info',
}
const status = computed(() => props.status ?? 'pending')
const presentation = computed(() => {
  const key = `status.${status.value}`
  const label = t(key)
  return { label: label === key ? status.value || t('status.unknown') : label, type: map[status.value] ?? 'info' as const }
})
</script>

<style scoped>
.status-dot { display: inline-block; width: 6px; height: 6px; margin-right: 6px; border-radius: 50%; background: currentColor; vertical-align: 1px; }
.is-processing, .is-publishing { animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: .35; } }
@media (prefers-reduced-motion: reduce) { .is-processing, .is-publishing { animation: none; } }
</style>
