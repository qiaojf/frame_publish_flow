<template>
  <div>
    <PageHeader :eyebrow="t('publish.eyebrow')" :title="t('publish.title')" :description="t('publish.intro')">
      <template #actions><el-button @click="$router.push('/publish/history')">{{ t('publish.viewHistory') }}</el-button></template>
    </PageHeader>
    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false" class="notice"><template #default><el-button text type="primary" @click="load">{{ t('common.reload') }}</el-button></template></el-alert>
    <div class="content-grid">
      <div>
        <section class="surface publish-section">
          <div class="surface-header"><div><h2>{{ t('publish.content') }}</h2><p>{{ t('publish.contentHint') }}</p></div></div>
          <div class="surface-body">
            <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
              <el-form-item :label="t('publish.targetVideo')" prop="video_id"><el-select v-model="form.video_id" filterable :placeholder="t('publish.selectVideo')" style="width: 100%" @change="syncVideoSelection"><el-option v-for="video in videos" :key="video.id" :label="video.title" :value="video.id"><span>{{ video.title }}</span><span class="option-code">{{ video.model_name }}</span></el-option></el-select></el-form-item>
              <el-form-item :label="t('publish.commonTitle')" prop="title"><el-input v-model="form.title" maxlength="120" show-word-limit :placeholder="t('publish.commonTitlePlaceholder')" /></el-form-item>
              <el-form-item :label="t('publish.commonDescription')"><el-input v-model="form.description" type="textarea" :rows="5" maxlength="2000" show-word-limit :placeholder="t('publish.commonDescriptionPlaceholder')" /></el-form-item>
              <el-form-item :label="t('publish.tags')"><el-select v-model="form.tags" multiple filterable allow-create default-first-option :placeholder="t('publish.tagsPlaceholder')" style="width: 100%" /></el-form-item>
              <el-form-item :label="t('publish.coverOptional')"><el-upload ref="coverUploadRef" :auto-upload="false" :limit="1" accept="image/jpeg,image/png,image/webp" :on-change="onCoverChange" :on-remove="removeCover"><el-button><el-icon><Upload /></el-icon>{{ t('publish.chooseCover') }}</el-button><template #tip><div class="el-upload__tip">{{ t('publish.coverTip') }}</div></template></el-upload></el-form-item>
            </el-form>
          </div>
        </section>

        <section v-if="resultTasks.length" class="surface result-section">
          <div class="surface-header"><div><h2>{{ t('publish.currentTasks') }}</h2><p>{{ t('publish.independentStatuses') }}</p></div><el-button text type="primary" @click="$router.push('/publish/history')">{{ t('publish.allRecords') }}</el-button></div>
          <div class="surface-body publish-result-list">
            <div v-for="task in resultTasks" :key="task.id" class="publish-result"><div><strong>{{ task.platform_name }}</strong><div class="item-meta">{{ task.account_name || t('common.defaultAccount') }} · <span class="mono">{{ task.id }}</span></div><p v-if="task.error_message" class="danger-text section-note">{{ getBusinessErrorMessage(task.error_code, task.error_message) }}</p></div><div><StatusTag :status="task.status" /><div v-if="cleanUrl(task.publish_url)" style="margin-top: 7px"><a class="link-button" :href="cleanUrl(task.publish_url)" target="_blank" rel="noopener">{{ t('publish.openResult') }}</a></div></div></div>
          </div>
        </section>
      </div>

      <aside class="surface">
        <div class="surface-header"><div><h2>{{ t('publish.targetPlatforms') }}</h2><p>{{ t('publish.targetPlatformsHint') }}</p></div><el-tag>{{ t('publish.selectedCount', { count: selectedPlatformIds.length }) }}</el-tag></div>
        <div class="surface-body">
          <DataState :loading="loading" :empty="!platforms.length" :empty-text="t('publish.noPlatforms')">
            <template #content><el-checkbox-group v-model="selectedPlatformIds" class="platform-list">
              <div v-for="platform in platforms" :key="platform.id" class="platform-card" :class="{ 'is-selected': isSelected(platform.id) }">
                <div class="platform-card-head"><el-checkbox :value="platform.id"><span class="platform-glyph">{{ platform.name.slice(0, 1).toUpperCase() }}</span></el-checkbox><div><strong>{{ platform.name }}</strong><div class="item-meta">{{ platform.description || platform.code }}</div></div></div>
                <div v-if="isSelected(platform.id)" class="platform-card-body">
                  <el-form label-position="top">
                    <el-form-item :label="t('publish.publishAccount')" required><el-select v-model="accountIds[platform.id]" :placeholder="t('publish.selectAccount')" style="width: 100%"><el-option v-for="account in enabledAccounts(platform)" :key="account.id" :label="account.name" :value="account.id"><span>{{ account.name }}</span><span class="option-code">{{ account.account_identifier }}</span></el-option></el-select></el-form-item>
                    <el-switch v-if="platform.capabilities.fields?.length" v-model="overrideEnabled[platform.id]" :disabled="requiresPublicVideoUrl(platform)" :active-text="t(requiresPublicVideoUrl(platform) ? 'publish.autoPublicUrl' : 'publish.overrideCommon')" />
                    <div v-if="overrideEnabled[platform.id]" class="override-panel"><DynamicCapabilityField v-for="field in platform.capabilities.fields" :key="field.key" v-model="overrides[platform.id][field.key]" :field="field" /></div>
                  </el-form>
                </div>
              </div>
            </el-checkbox-group></template>
          </DataState>
          <div class="form-footer"><el-button type="primary" size="large" :loading="submitting" @click="submit"><el-icon><Promotion /></el-icon>{{ t('publish.createTasks') }}</el-button></div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { Promotion, Upload } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules, type UploadFile, type UploadInstance } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import DataState from '@/components/DataState.vue'
import StatusTag from '@/components/StatusTag.vue'
import DynamicCapabilityField from '@/components/DynamicCapabilityField.vue'
import { getVideos } from '@/api/videos'
import { getPublishPlatforms } from '@/api/platforms'
import { createPublishTasks, getPublishTask } from '@/api/publish'
import type { VideoAsset } from '@/types/video'
import type { PublishPlatform } from '@/types/platform'
import type { PublishTask } from '@/types/publish'
import { getBusinessErrorMessage, getErrorMessage } from '@/utils/errors'
import { cleanUrl } from '@/utils/url'

const route = useRoute()
const { t } = useI18n()
const formRef = ref<FormInstance>(); const coverUploadRef = ref<UploadInstance>()
const loading = ref(true); const submitting = ref(false); const loadError = ref('')
const videos = ref<VideoAsset[]>([]); const platforms = ref<PublishPlatform[]>([]); const selectedPlatformIds = ref<string[]>([])
const accountIds = reactive<Record<string, string>>({}); const overrideEnabled = reactive<Record<string, boolean>>({}); const overrides = reactive<Record<string, Record<string, unknown>>>({})
const cover = ref<File>(); const resultTasks = ref<PublishTask[]>([])
const form = reactive({ video_id: '', title: '', description: '', tags: [] as string[] })
const rules = computed<FormRules<typeof form>>(() => ({ video_id: [{ required: true, message: t('publish.videoRequired'), trigger: 'change' }], title: [{ required: true, message: t('publish.titleRequired'), trigger: 'blur' }] }))
const interval = Number(import.meta.env.VITE_POLL_INTERVAL_MS ?? 4000); let pollTimer: number | undefined

function isSelected(id: string) { return selectedPlatformIds.value.includes(id) }
function enabledAccounts(platform: PublishPlatform) { return (platform.accounts ?? []).filter((item) => item.enabled) }
function requiresPublicVideoUrl(platform: PublishPlatform) { return platform.capabilities.requires_public_media_url === true || Boolean(platform.capabilities.fields?.some((field) => field.key === 'video_url')) }
function capabilityFieldLabel(key: string, fallback: string) {
  const translationKey = ({ video_url: 'publish.fieldVideoUrl', caption: 'publish.fieldCaption', share_to_feed: 'publish.fieldShareToFeed' } as const)[key as 'video_url' | 'caption' | 'share_to_feed']
  return translationKey ? t(translationKey) : fallback
}
function buildPublicVideoUrl(videoId: string) { return new URL(`/videos-pub/${encodeURIComponent(videoId)}`, window.location.origin).toString() }
function syncPlatformVideoUrl(platform: PublishPlatform) {
  if (!overrides[platform.id]) overrides[platform.id] = {}
  if (!requiresPublicVideoUrl(platform) || !form.video_id) return
  overrides[platform.id].video_url = buildPublicVideoUrl(form.video_id)
  overrideEnabled[platform.id] = true
}
function syncVideoSelection(id: string) {
  const video = videos.value.find((item) => item.id === id)
  if (video && !form.title) form.title = video.title
  selectedPlatformIds.value.forEach((platformId) => {
    const platform = platforms.value.find((item) => item.id === platformId)
    if (platform) syncPlatformVideoUrl(platform)
  })
}

watch(selectedPlatformIds, (ids) => {
  ids.forEach((id) => {
    if (!overrides[id]) overrides[id] = {}
    if (overrideEnabled[id] === undefined) overrideEnabled[id] = false
    const platform = platforms.value.find((item) => item.id === id)
    if (platform) syncPlatformVideoUrl(platform)
  })
})

async function load() {
  loading.value = true; loadError.value = ''
  const [videoResult, platformResult] = await Promise.allSettled([getVideos({ page: 1, page_size: 100, status: 'success' }), getPublishPlatforms()])
  if (videoResult.status === 'fulfilled') videos.value = videoResult.value.items
  if (platformResult.status === 'fulfilled') platforms.value = platformResult.value.filter((item) => item.enabled)
  if (videoResult.status === 'rejected' || platformResult.status === 'rejected') loadError.value = t('publish.loadFailed')
  const queryVideo = typeof route.query.video === 'string' ? route.query.video : ''
  if (queryVideo && videos.value.some((item) => item.id === queryVideo)) { form.video_id = queryVideo; syncVideoSelection(queryVideo) }
  loading.value = false
}

function onCoverChange(file: UploadFile) {
  if (!file.raw) return
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.raw.type)) { ElMessage.error(t('publish.coverTypes')); coverUploadRef.value?.clearFiles(); return }
  const maxMb = Number(import.meta.env.VITE_MAX_IMAGE_SIZE_MB ?? 10)
  if (file.raw.size > maxMb * 1024 * 1024) { ElMessage.error(t('publish.coverMax', { size: maxMb })); coverUploadRef.value?.clearFiles(); return }
  cover.value = file.raw
}
function removeCover() { cover.value = undefined }

function validateTargets(): boolean {
  if (!selectedPlatformIds.value.length) { ElMessage.error(t('publish.platformRequired')); return false }
  for (const id of selectedPlatformIds.value) {
    const platform = platforms.value.find((item) => item.id === id)
    if (!accountIds[id]) { ElMessage.error(t('publish.accountRequired', { platform: platform?.name ?? t('common.platform') })); return false }
    if (overrideEnabled[id]) {
      const missing = platform?.capabilities.fields?.find((field) => field.required && !overrides[id][field.key])
      if (missing) { ElMessage.error(t('publish.fieldRequired', { platform: platform?.name, field: capabilityFieldLabel(missing.key, missing.label) })); return false }
    }
  }
  return true
}

async function submit() {
  if (!(await formRef.value?.validate().catch(() => false)) || !validateTargets()) return
  submitting.value = true
  try {
    const result = await createPublishTasks({ ...form, cover: cover.value, targets: selectedPlatformIds.value.map((id) => ({ platform_id: id, account_id: accountIds[id], overrides: overrideEnabled[id] ? overrides[id] : undefined })) })
    resultTasks.value = result.tasks
    ElMessage.success(t('publish.tasksCreated', { count: result.tasks.length }))
    schedulePoll()
  } catch (reason) { ElMessage.error(getErrorMessage(reason, t('publish.taskCreateFailed'))) }
  finally { submitting.value = false }
}

function schedulePoll() {
  window.clearTimeout(pollTimer)
  if (!resultTasks.value.some((task) => ['pending', 'publishing'].includes(task.status))) return
  pollTimer = window.setTimeout(pollTasks, interval)
}
async function pollTasks() {
  const pending = resultTasks.value.filter((task) => ['pending', 'publishing'].includes(task.status))
  const settled = await Promise.allSettled(pending.map((task) => getPublishTask(task.id)))
  settled.forEach((result) => { if (result.status === 'fulfilled') { const index = resultTasks.value.findIndex((task) => task.id === result.value.id); if (index >= 0) resultTasks.value[index] = result.value } })
  schedulePoll()
}

onMounted(load)
onBeforeUnmount(() => window.clearTimeout(pollTimer))
</script>

<style scoped>
.notice, .result-section { margin-bottom: 20px; }
.publish-section { margin-bottom: 20px; }
.option-code { float: right; margin-left: 26px; color: var(--ink-500); font-size: 11px; }
.platform-card-head :deep(.el-checkbox__label) { display: inline-flex; padding-left: 10px; }
</style>
