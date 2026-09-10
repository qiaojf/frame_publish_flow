<template>
  <div v-if="loading" class="data-state"><el-skeleton :rows="rows" animated /></div>
  <el-result v-else-if="error" icon="error" title="数据暂时不可用" :sub-title="error">
    <template #extra><el-button type="primary" @click="$emit('retry')">重新加载</el-button></template>
  </el-result>
  <el-empty v-else-if="empty" :description="emptyText" :image-size="84"><slot /></el-empty>
  <slot v-else name="content" />
</template>

<script setup lang="ts">
withDefaults(defineProps<{ loading?: boolean; error?: string; empty?: boolean; emptyText?: string; rows?: number }>(), {
  loading: false, error: '', empty: false, emptyText: '暂无数据', rows: 5,
})
defineEmits<{ retry: [] }>()
</script>

<style scoped>.data-state { padding: 26px; }</style>
