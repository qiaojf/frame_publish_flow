<template>
  <div>
    <PageHeader eyebrow="Create" title="制作视频" description="只需描述画面；添加参考图后，后端会自动按图生视频处理。">
      <template #actions><el-button @click="$router.push('/videos')">返回我的视频</el-button></template>
    </PageHeader>

    <el-alert v-if="prefillNotice" :title="prefillNotice" type="info" show-icon class="notice" closable />
    <div class="creation-grid">
      <section class="surface">
        <div class="surface-header"><div><h2>创作内容</h2><p>描述主体、环境、镜头与动作，画面会更稳定。</p></div><el-tag effect="plain">{{ modeLabel }}</el-tag></div>
        <div class="surface-body">
          <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
            <el-form-item :label="promptLabel" prop="prompt">
              <el-input v-model="form.prompt" class="prompt-input" type="textarea" :maxlength="promptMaxLength" show-word-limit resize="vertical" placeholder="例如：雨后的东京街道，镜头沿路面缓慢前移，霓虹倒影随着车流轻轻变化……" />
            </el-form-item>
            <el-form-item label="参考图片（可选）">
              <div v-if="previewUrl" class="image-preview">
                <img :src="previewUrl" alt="已选择的参考图片预览" />
                <el-button class="remove-image" type="danger" circle :icon="Delete" aria-label="删除参考图片" @click="removeImage" />
              </div>
              <el-upload v-else ref="uploadRef" class="upload-zone" :auto-upload="false" :show-file-list="false" accept="image/jpeg,image/png,image/webp" :on-change="onFileChange">
                <div class="upload-card"><div><el-icon :size="25"><Picture /></el-icon><strong>选择一张参考图片</strong><small>JPG、PNG、WebP；大小上限由配置或模型能力决定</small></div></div>
              </el-upload>
            </el-form-item>
            <div class="form-footer"><el-button type="primary" size="large" :loading="submitting" :disabled="modelsLoading" @click="submit"><el-icon><VideoPlay /></el-icon>生成视频</el-button></div>
          </el-form>
        </div>
      </section>

      <aside>
        <section class="surface">
          <div class="surface-header"><div><h2>生成设置</h2><p>选项由当前模型动态提供</p></div></div>
          <div class="surface-body">
            <el-alert v-if="modelsError" :title="modelsError" type="error" show-icon :closable="false" class="notice"><template #default><el-button text type="primary" @click="loadModels">重新加载</el-button></template></el-alert>
            <el-form :model="form" label-position="top">
              <el-form-item label="视频生成模型" required>
                <el-select v-model="form.model_id" :loading="modelsLoading" placeholder="请选择已启用的模型" filterable style="width: 100%" @change="resetCapabilities">
                  <el-option v-for="model in models" :key="model.id" :label="model.name" :value="model.id"><span>{{ model.name }}</span><span class="option-code">{{ model.code }}</span></el-option>
                </el-select>
                <div v-if="selectedModel" class="capability-row"><el-tag size="small" :type="selectedModel.supports_text_to_video ? 'success' : 'info'">文生视频</el-tag><el-tag size="small" :type="selectedModel.supports_image_to_video ? 'success' : 'info'">图生视频</el-tag></div>
              </el-form-item>
              <el-form-item v-if="durations.length" label="视频时长"><el-radio-group v-model="form.duration"><el-radio-button v-for="duration in durations" :key="duration" :value="duration">{{ duration }} 秒</el-radio-button></el-radio-group></el-form-item>
              <el-form-item v-if="aspectRatios.length" label="画面比例"><el-select v-model="form.aspect_ratio" placeholder="请选择比例" style="width: 100%"><el-option v-for="ratio in aspectRatios" :key="ratio" :label="ratio" :value="ratio" /></el-select></el-form-item>
              <el-form-item v-if="resolutions.length" label="分辨率"><el-select v-model="form.resolution" placeholder="请选择分辨率" style="width: 100%"><el-option v-for="resolution in resolutions" :key="resolution" :label="resolution" :value="resolution" /></el-select></el-form-item>
            </el-form>
            <div class="mode-callout"><el-icon :size="18"><InfoFilled /></el-icon><div><strong>{{ modeLabel }}</strong><p>{{ modeDescription }}</p></div></div>
          </div>
        </section>

        <section v-if="task" class="task-track">
          <div class="task-track-head"><div><strong>生成任务</strong><div class="item-meta mono">{{ task.id }}</div></div><StatusTag :status="task.status" /></div>
          <div class="task-track-bar"><span v-for="step in 4" :key="step" :class="{ active: step <= activeSteps }" /></div>
          <p class="section-note">{{ taskMessage }}</p>
          <p v-if="task.error_message" class="danger-text section-note">{{ task.error_message }}</p>
          <el-button v-if="task.status === 'success' && task.video_id" type="primary" plain style="margin-top: 14px" @click="$router.push(`/videos/${task.video_id}`)">查看生成结果</el-button>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Delete, InfoFilled, Picture, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules, type UploadFile, type UploadInstance } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import { getVideoModels } from '@/api/models'
import { createGenerationTask, getGenerationTask } from '@/api/generation'
import { getVideo } from '@/api/videos'
import type { VideoModelOption } from '@/types/video-model'
import type { GenerationTask } from '@/types/generation'
import { getErrorMessage } from '@/utils/errors'

const route = useRoute()
const formRef = ref<FormInstance>()
const uploadRef = ref<UploadInstance>()
const models = ref<VideoModelOption[]>([])
const modelsLoading = ref(false)
const modelsError = ref('')
const submitting = ref(false)
const imageFile = ref<File>()
const previewUrl = ref('')
const task = ref<GenerationTask>()
const prefillNotice = ref('')
let pollTimer: number | undefined
const interval = Number(import.meta.env.VITE_POLL_INTERVAL_MS ?? 4000)

const form = reactive<{ prompt: string; model_id: string; duration?: number; aspect_ratio?: string; resolution?: string }>({ prompt: '', model_id: '' })
const selectedModel = computed(() => models.value.find((item) => item.id === form.model_id))
const durations = computed(() => selectedModel.value?.capabilities.durations ?? [])
const aspectRatios = computed(() => selectedModel.value?.capabilities.aspect_ratios ?? [])
const resolutions = computed(() => {
  const available = selectedModel.value?.capabilities.resolutions ?? []
  const matrix = selectedModel.value?.capabilities.resolution_duration_matrix
  if (!matrix || form.duration === undefined) return available
  return available.filter((resolution) => matrix[resolution]?.includes(form.duration as number) ?? true)
})
const modeLabel = computed(() => imageFile.value ? '图生视频' : '文生视频')
const modeDescription = computed(() => imageFile.value ? '已添加参考图，提交后由后端按图生视频能力处理。' : '未添加参考图，提交后由后端按文生视频能力处理。')
const promptRequired = computed(() => imageFile.value
  ? selectedModel.value?.capabilities.prompt?.required_for_image_to_video !== false
  : selectedModel.value?.capabilities.prompt?.required_for_text_to_video !== false)
const promptMaxLength = computed(() => selectedModel.value?.capabilities.prompt?.max_length ?? 2000)
const promptLabel = computed(() => promptRequired.value ? '视频描述' : '视频描述（可选）')
const rules: FormRules<typeof form> = {
  prompt: [{
    trigger: 'blur',
    validator: (_rule, value: string, callback) => {
      const normalized = (value ?? '').trim()
      if (promptRequired.value && !normalized) return callback(new Error('请输入视频描述'))
      if (normalized && normalized.length < 3) return callback(new Error('请至少输入 3 个字符'))
      if (normalized.length > promptMaxLength.value) return callback(new Error(`视频描述不能超过 ${promptMaxLength.value} 个字符`))
      callback()
    },
  }],
}
const activeSteps = computed(() => task.value?.status === 'success' ? 4 : task.value?.status === 'processing' ? 2 : 1)
const taskMessage = computed(() => ({ pending: '任务已提交，正在等待生成资源。', processing: '视频正在生成中；后端未返回真实进度时不显示百分比。', success: '视频已生成，可以查看结果。', failed: '生成失败，请根据错误信息调整后重试。', cancelled: '任务已取消。', timeout: '任务处理超时。' }[task.value?.status ?? 'pending']))

function resetCapabilities() {
  form.duration = durations.value[0]
  form.aspect_ratio = aspectRatios.value[0]
  form.resolution = resolutions.value[0]
  if (imageFile.value && selectedModel.value && !selectedModel.value.supports_image_to_video) removeImage()
}

async function loadModels() {
  modelsLoading.value = true; modelsError.value = ''
  try {
    models.value = await getVideoModels()
    if (!form.model_id && models.value.length) { form.model_id = models.value[0].id; resetCapabilities() }
  } catch (error) { modelsError.value = getErrorMessage(error, '模型列表加载失败') }
  finally { modelsLoading.value = false }
}

function onFileChange(uploadFile: UploadFile) {
  const file = uploadFile.raw
  if (!file) return
  const allowed = ['image/jpeg', 'image/png', 'image/webp']
  if (!allowed.includes(file.type)) { ElMessage.error('仅支持 JPG、PNG 或 WebP 图片'); uploadRef.value?.clearFiles(); return }
  const configuredMax = Number(import.meta.env.VITE_MAX_IMAGE_SIZE_MB ?? 10)
  const exclusiveMax = selectedModel.value?.capabilities.image?.max_size_mb_exclusive
  const maxMb = exclusiveMax ?? selectedModel.value?.capabilities.max_image_size_mb ?? configuredMax
  const tooLarge = exclusiveMax !== undefined
    ? file.size >= maxMb * 1024 * 1024
    : file.size > maxMb * 1024 * 1024
  if (tooLarge) { ElMessage.error(exclusiveMax !== undefined ? `图片大小必须小于 ${maxMb} MB` : `图片大小不能超过 ${maxMb} MB`); uploadRef.value?.clearFiles(); return }
  if (selectedModel.value && !selectedModel.value.supports_image_to_video) { ElMessage.error('当前模型不支持图生视频，请先切换模型'); uploadRef.value?.clearFiles(); return }
  removeImage(); imageFile.value = file; previewUrl.value = URL.createObjectURL(file)
}

function removeImage() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''; imageFile.value = undefined; uploadRef.value?.clearFiles()
}

function validateCapability(): boolean {
  if (!selectedModel.value) { ElMessage.error('请选择视频生成模型'); return false }
  if (imageFile.value && !selectedModel.value.supports_image_to_video) { ElMessage.error('当前模型不支持图生视频'); return false }
  if (!imageFile.value && !selectedModel.value.supports_text_to_video) { ElMessage.error('当前模型不支持文生视频'); return false }
  return true
}

async function submit() {
  if (!(await formRef.value?.validate().catch(() => false)) || !validateCapability()) return
  submitting.value = true
  try {
    task.value = await createGenerationTask({ ...form, image: imageFile.value })
    ElMessage.success('生成任务已创建')
    schedulePoll()
  } catch (error) { ElMessage.error(getErrorMessage(error, '生成任务创建失败')) }
  finally { submitting.value = false }
}

function schedulePoll() {
  window.clearTimeout(pollTimer)
  if (!task.value || !['pending', 'processing'].includes(task.value.status)) return
  pollTimer = window.setTimeout(poll, interval)
}

async function poll() {
  if (!task.value) return
  try { task.value = await getGenerationTask(task.value.id); schedulePoll() }
  catch (error) { ElMessage.error(getErrorMessage(error, '任务状态查询失败')) }
}

async function prefillRegeneration() {
  const id = typeof route.query.regenerate === 'string' ? route.query.regenerate : ''
  if (!id) return
  try {
    const video = await getVideo(id)
    form.prompt = video.prompt; form.model_id = video.model_id ?? ''; form.duration = video.duration; form.aspect_ratio = video.aspect_ratio; form.resolution = video.resolution
    prefillNotice.value = `已从“${video.title}”带入生成参数，请确认后创建新任务。`
  } catch (error) { prefillNotice.value = getErrorMessage(error, '原视频参数加载失败') }
}

onMounted(async () => { await loadModels(); await prefillRegeneration() })
onBeforeUnmount(() => { window.clearTimeout(pollTimer); removeImage() })
watch(() => form.duration, () => {
  if (form.resolution && !resolutions.value.includes(form.resolution)) form.resolution = resolutions.value[0]
})
</script>

<style scoped>
.notice { margin-bottom: 16px; }
.option-code { float: right; margin-left: 26px; color: var(--ink-500); font: 11px "Cascadia Code", monospace; }
</style>
