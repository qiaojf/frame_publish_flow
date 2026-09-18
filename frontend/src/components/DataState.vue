<template>
  <div v-if="loading" class="data-state"><el-skeleton :rows="rows" animated /></div>
  <el-result v-else-if="error" icon="error" :title="t('common.dataUnavailable')" :sub-title="error">
    <template #extra><el-button type="primary" @click="$emit('retry')">{{ t('common.reload') }}</el-button></template>
  </el-result>
  <el-empty v-else-if="empty" :description="emptyText || defaultEmptyText" :image-size="84"><slot /></el-empty>
  <slot v-else name="content" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const defaultEmptyText = computed(() => t('common.noData'))
withDefaults(defineProps<{ loading?: boolean; error?: string; empty?: boolean; emptyText?: string; rows?: number }>(), {
  loading: false, error: '', empty: false, emptyText: undefined, rows: 5,
})
defineEmits<{ retry: [] }>()
</script>

<style scoped>.data-state { padding: 26px; }</style>
