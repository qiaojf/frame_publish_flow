<template>
  <div>
    <PageHeader eyebrow="Distribute" title="发布视频" description="选择多个目标平台并一次提交；后端会为每个平台建立独立发布任务。">
      <template #actions><el-button @click="$router.push('/publish/history')">查看发布记录</el-button></template>
    </PageHeader>
    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false" class="notice"><template #default><el-button text type="primary" @click="load">重新加载</el-button></template></el-alert>
    <div class="content-grid">
      <div>
        <section class="surface publish-section">
          <div class="surface-header"><div><h2>发布内容</h2><p>公共内容会用于所有目标平台</p></div></div>
          <div class="surface-body">
            <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
              <el-form-item label="目标视频" prop="video_id"><el-select v-model="form.video_id" filterable placeholder="请选择要发布的视频" style="width: 100%" @change="syncVideoSelection"><el-option v-for="video in videos" :key="video.id" :label="video.title" :value="video.id"><span>{{ video.title }}</span><span class="option-code">{{ video.model_name }}</span></el-option></el-select></el-form-item>
              <el-form-item label="公共标题" prop="title"><el-input v-model="form.title" maxlength="120" show-word-limit placeholder="输入各平台默认使用的标题" /></el-form-item>
              <el-form-item label="公共描述"><el-input v-model="form.description" type="textarea" :rows="5" maxlength="2000" show-word-limit placeholder="输入视频说明或发布正文" /></el-form-item>
              <el-form-item label="Tags / Hashtags"><el-select v-model="form.tags" multiple filterable allow-create default-first-option placeholder="输入后按回车添加" style="width: 100%" /></el-form-item>
              <el-form-item label="公共封面（可选）"><el-upload ref="coverUploadRef" :auto-upload="false" :limit="1" accept="image/jpeg,image/png,image/webp" :on-change="onCoverChange" :on-remove="removeCover"><el-button><el-icon><Upload /></el-icon>选择封面</el-button><template #tip><div class="el-upload__tip">JPG、PNG、WebP；实际平台是否支持由 capabilities 决定。</div></template></el-upload></el-form-item>
            </el-form>
          </div>
        </section>

        <section v-if="resultTasks.length" class="surface result-section">
          <div class="surface-header"><div><h2>本次发布任务</h2><p>各平台状态互不影响</p></div><el-button text type="primary" @click="$router.push('/publish/history')">全部记录</el-button></div>
          <div class="surface-body publish-result-list">
            <div v-for="task in resultTasks" :key="task.id" class="publish-result"><div><strong>{{ task.platform_name }}</strong><div class="item-meta">{{ task.account_name || '默认账号' }} · <span class="mono">{{ task.id }}</span></div><p v-if="task.error_message" class="danger-text section-note">{{ task.error_message }}</p></div><div><StatusTag :status="task.status" /><div v-if="task.publish_url" style="margin-top: 7px"><a class="link-button" :href="task.publish_url" target="_blank" rel="noopener">打开结果</a></div></div></div>
          </div>
        </section>
      </div>

      <aside class="surface">
        <div class="surface-header"><div><h2>目标平台</h2><p>为每个平台选择发布账号</p></div><el-tag>{{ selectedPlatformIds.length }} 已选</el-tag></div>
        <div class="surface-body">
          <DataState :loading="loading" :empty="!platforms.length" empty-text="后端尚未返回可用发布平台">
            <template #content><el-checkbox-group v-model="selectedPlatformIds" class="platform-list">
              <div v-for="platform in platforms" :key="platform.id" class="platform-card" :class="{ 'is-selected': isSelected(platform.id) }">
                <div class="platform-card-head"><el-checkbox :value="platform.id"><span class="platform-glyph">{{ platform.name.slice(0, 1).toUpperCase() }}</span></el-checkbox><div><strong>{{ platform.name }}</strong><div class="item-meta">{{ platform.description || platform.code }}</div></div></div>
                <div v-if="isSelected(platform.id)" class="platform-card-body">
                  <el-form label-position="top">
                    <el-form-item label="发布账号" required><el-select v-model="accountIds[platform.id]" placeholder="选择已启用账号" style="width: 100%"><el-option v-for="account in enabledAccounts(platform)" :key="account.id" :label="account.name" :value="account.id"><span>{{ account.name }}</span><span class="option-code">{{ account.account_identifier }}</span></el-option></el-select></el-form-item>
                    <el-switch v-if="platform.capabilities.fields?.length" v-model="overrideEnabled[platform.id]" :disabled="requiresPublicVideoUrl(platform)" :active-text="requiresPublicVideoUrl(platform) ? '已自动填入公网视频 URL' : '覆盖公共内容'" />
                    <div v-if="overrideEnabled[platform.id]" class="override-panel"><DynamicCapabilityField v-for="field in platform.capabilities.fields" :key="field.key" v-model="overrides[platform.id][field.key]" :field="field" /></div>
                  </el-form>
                </div>
              </div>
            </el-checkbox-group></template>
          </DataState>
          <div class="form-footer"><el-button type="primary" size="large" :loading="submitting" @click="submit"><el-icon><Promotion /></el-icon>创建发布任务</el-button></div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
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
import { getErrorMessage } from '@/utils/errors'

const route = useRoute()
const formRef = ref<FormInstance>(); const coverUploadRef = ref<UploadInstance>()
const loading = ref(true); const submitting = ref(false); const loadError = ref('')
const videos = ref<VideoAsset[]>([]); const platforms = ref<PublishPlatform[]>([]); const selectedPlatformIds = ref<string[]>([])
const accountIds = reactive<Record<string, string>>({}); const overrideEnabled = reactive<Record<string, boolean>>({}); const overrides = reactive<Record<string, Record<string, unknown>>>({})
const cover = ref<File>(); const resultTasks = ref<PublishTask[]>([])
const form = reactive({ video_id: '', title: '', description: '', tags: [] as string[] })
const rules: FormRules<typeof form> = { video_id: [{ required: true, message: '请选择目标视频', trigger: 'change' }], title: [{ required: true, message: '请输入公共标题', trigger: 'blur' }] }
const interval = Number(import.meta.env.VITE_POLL_INTERVAL_MS ?? 4000); let pollTimer: number | undefined

function isSelected(id: string) { return selectedPlatformIds.value.includes(id) }
function enabledAccounts(platform: PublishPlatform) { return (platform.accounts ?? []).filter((item) => item.enabled) }
function requiresPublicVideoUrl(platform: PublishPlatform) { return platform.capabilities.requires_public_media_url === true || Boolean(platform.capabilities.fields?.some((field) => field.key === 'video_url')) }
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
  if (videoResult.status === 'rejected' || platformResult.status === 'rejected') loadError.value = '视频或平台数据加载失败，请确认后端服务已就绪。'
  const queryVideo = typeof route.query.video === 'string' ? route.query.video : ''
  if (queryVideo && videos.value.some((item) => item.id === queryVideo)) { form.video_id = queryVideo; syncVideoSelection(queryVideo) }
  loading.value = false
}

function onCoverChange(file: UploadFile) {
  if (!file.raw) return
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.raw.type)) { ElMessage.error('封面仅支持 JPG、PNG 或 WebP'); coverUploadRef.value?.clearFiles(); return }
  const maxMb = Number(import.meta.env.VITE_MAX_IMAGE_SIZE_MB ?? 10)
  if (file.raw.size > maxMb * 1024 * 1024) { ElMessage.error(`封面大小不能超过 ${maxMb} MB`); coverUploadRef.value?.clearFiles(); return }
  cover.value = file.raw
}
function removeCover() { cover.value = undefined }

function validateTargets(): boolean {
  if (!selectedPlatformIds.value.length) { ElMessage.error('请至少选择一个发布平台'); return false }
  for (const id of selectedPlatformIds.value) {
    const platform = platforms.value.find((item) => item.id === id)
    if (!accountIds[id]) { ElMessage.error(`请选择 ${platform?.name ?? '平台'} 的发布账号`); return false }
    if (overrideEnabled[id]) {
      const missing = platform?.capabilities.fields?.find((field) => field.required && !overrides[id][field.key])
      if (missing) { ElMessage.error(`请填写 ${platform?.name} 的${missing.label}`); return false }
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
    ElMessage.success(`已创建 ${result.tasks.length} 个独立发布任务`)
    schedulePoll()
  } catch (reason) { ElMessage.error(getErrorMessage(reason, '发布任务创建失败')) }
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
