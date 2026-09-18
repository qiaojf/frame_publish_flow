<template>
  <el-form-item :label="fieldLabel" :required="field.required">
    <el-input v-if="field.type === 'text'" :model-value="stringValue" :maxlength="field.max_length" show-word-limit :placeholder="field.placeholder" @update:model-value="update" />
    <el-input v-else-if="field.type === 'textarea'" :model-value="stringValue" type="textarea" :rows="3" :maxlength="field.max_length" show-word-limit :placeholder="field.placeholder" @update:model-value="update" />
    <el-input-number v-else-if="field.type === 'number'" :model-value="numberValue" controls-position="right" style="width: 100%" @update:model-value="update" />
    <el-switch v-else-if="field.type === 'boolean'" :model-value="booleanValue" @update:model-value="update" />
    <el-select v-else-if="field.type === 'select'" :model-value="stringValue" :placeholder="field.placeholder || t('common.select')" style="width: 100%" @update:model-value="update">
      <el-option v-for="option in options" :key="option.value" :label="option.label" :value="option.value" />
    </el-select>
    <el-select v-else :model-value="arrayValue" multiple filterable allow-create default-first-option :placeholder="field.placeholder || t('common.addByEnter')" style="width: 100%" @update:model-value="update">
      <el-option v-for="option in options" :key="option.value" :label="option.label" :value="option.value" />
    </el-select>
  </el-form-item>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PlatformCapabilityField } from '@/types/platform'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ field: PlatformCapabilityField; modelValue?: unknown }>()
const emit = defineEmits<{ 'update:modelValue': [value: unknown] }>()
const { t } = useI18n()
const stringValue = computed(() => typeof props.modelValue === 'string' ? props.modelValue : '')
const numberValue = computed(() => typeof props.modelValue === 'number' ? props.modelValue : undefined)
const booleanValue = computed(() => Boolean(props.modelValue))
const arrayValue = computed(() => Array.isArray(props.modelValue) ? props.modelValue.map(String) : [])
const options = computed(() => (props.field.options ?? []).map((item) => typeof item === 'string' ? { label: item, value: item } : item))
const fieldLabel = computed(() => {
  const key = ({ video_url: 'publish.fieldVideoUrl', caption: 'publish.fieldCaption', share_to_feed: 'publish.fieldShareToFeed' } as const)[props.field.key as 'video_url' | 'caption' | 'share_to_feed']
  return key ? t(key) : props.field.label
})
function update(value: unknown) { emit('update:modelValue', value) }
</script>
