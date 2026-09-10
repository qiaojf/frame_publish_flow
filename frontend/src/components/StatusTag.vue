<template>
  <el-tag :type="presentation.type" :effect="['processing', 'publishing'].includes(status) ? 'dark' : 'light'" round>
    <span class="status-dot" :class="`is-${status}`" />{{ presentation.label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TagProps } from 'element-plus'

const props = defineProps<{ status?: string }>()
const map: Record<string, { label: string; type: TagProps['type'] }> = {
  pending: { label: '等待中', type: 'info' }, processing: { label: '处理中', type: 'primary' },
  publishing: { label: '发布中', type: 'primary' },
  success: { label: '成功', type: 'success' }, failed: { label: '失败', type: 'danger' },
  cancelled: { label: '已取消', type: 'info' }, timeout: { label: '已超时', type: 'warning' },
  not_published: { label: '未发布', type: 'info' }, partially_failed: { label: '部分失败', type: 'warning' },
  enabled: { label: '已启用', type: 'success' }, disabled: { label: '已停用', type: 'info' },
}
const status = computed(() => props.status ?? 'pending')
const presentation = computed(() => map[status.value] ?? { label: status.value, type: 'info' as const })
</script>

<style scoped>
.status-dot { display: inline-block; width: 6px; height: 6px; margin-right: 6px; border-radius: 50%; background: currentColor; vertical-align: 1px; }
.is-processing, .is-publishing { animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: .35; } }
@media (prefers-reduced-motion: reduce) { .is-processing, .is-publishing { animation: none; } }
</style>
