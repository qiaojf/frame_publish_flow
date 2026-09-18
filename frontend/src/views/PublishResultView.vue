<template>
  <div>
    <PageHeader
      :eyebrow="t('publish.receiptEyebrow')"
      :title="task?.video_title || t('publish.resultTitle')"
      :description="t('publish.resultIntro')"
    >
      <template #actions>
        <el-button @click="$router.push('/publish/history')"><el-icon><Back /></el-icon>{{ t('publish.backHistory') }}</el-button>
        <el-button v-if="task" type="primary" @click="$router.push(`/videos/${task.video_id}`)">{{ t('publish.viewSource') }}</el-button>
      </template>
    </PageHeader>

    <DataState :loading="loading" :error="error" :empty="!task" :empty-text="t('publish.resultNotFound')" @retry="load">
      <template #content>
        <div v-if="task" class="delivery-grid">
          <section class="surface delivery-stage">
            <div class="delivery-stage-head">
              <div>
                <span class="stage-kicker">{{ task.platform_name }} · {{ publishTypeLabel }}</span>
                <h2>{{ task.video_title || t('common.untitledVideo') }}</h2>
              </div>
              <StatusTag :status="task.status" />
            </div>
            <div class="player-frame">
              <video
                v-if="relativeVideoUrl"
                class="video-player"
                :src="relativeVideoUrl"
                :poster="task.video_thumbnail_url"
                controls
                preload="metadata"
              >{{ t('video.browserUnsupported') }}</video>
              <div v-else class="player-empty"><VideoPlay :size="36" /><span>{{ t('publish.missingVideoPath') }}</span></div>
            </div>
            <div class="stage-foot">
              <span>{{ t('publish.accountLabel', { account: task.account_name || t('common.defaultAccount') }) }}</span>
              <span>{{ t('publish.completedAt', { time: formatDate(task.published_at || task.created_at) }) }}</span>
            </div>
          </section>

          <aside class="surface receipt-card">
            <div class="receipt-signal" :class="`is-${task.status}`" />
            <div class="receipt-head">
              <span class="page-eyebrow">{{ t('publish.receiptEyebrow') }}</span>
              <h2>{{ t('publish.receipt') }}</h2>
              <p>{{ t('publish.relativePathHint') }}</p>
            </div>

            <div class="receipt-id-block">
              <span>{{ t('publish.postId') }}</span>
              <strong class="mono">{{ task.platform_post_id || postId }}</strong>
              <el-button text type="primary" @click="copyPostId"><el-icon><CopyDocument /></el-icon>{{ t('common.copy') }}</el-button>
            </div>

            <dl class="receipt-list">
              <dt>{{ t('common.platform') }}</dt><dd>{{ task.platform_name }}</dd>
              <dt>{{ t('common.account') }}</dt><dd>{{ task.account_name || t('common.defaultAccount') }}</dd>
              <dt>{{ t('publish.taskId') }}</dt><dd class="mono">{{ task.id }}</dd>
              <template v-if="task.provider_container_id"><dt>{{ t('publish.containerId') }}</dt><dd class="mono">{{ task.provider_container_id }}</dd></template>
              <template v-if="task.provider_upload_id"><dt>{{ t('publish.uploadId') }}</dt><dd class="mono">{{ task.provider_upload_id }}</dd></template>
              <dt>{{ t('publish.internalPath') }}</dt><dd class="mono">/publish/{{ task.platform_post_id || postId }}</dd>
              <dt>{{ t('publish.videoPath') }}</dt><dd class="mono">{{ relativeVideoUrl || '—' }}</dd>
            </dl>

            <div v-if="task.error_message" class="receipt-error">
              <strong>{{ task.error_code || t('publish.publishFailed') }}</strong>
              <p>{{ getBusinessErrorMessage(task.error_code, task.error_message) }}</p>
            </div>
          </aside>
        </div>
      </template>
    </DataState>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { Back, CopyDocument, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import DataState from '@/components/DataState.vue'
import StatusTag from '@/components/StatusTag.vue'
import { getPublishedPost } from '@/api/publish'
import type { PublishTask } from '@/types/publish'
import { formatDate } from '@/utils/format'
import { getBusinessErrorMessage, getErrorMessage } from '@/utils/errors'

const route = useRoute()
const { t } = useI18n()
const postId = String(route.params.postId)
const task = ref<PublishTask>()
const loading = ref(true)
const error = ref('')

const publishTypeLabel = computed(() => ({ reel: 'Reel', post: t('publish.typePost'), video: t('publish.typeVideo') }[task.value?.publish_type ?? 'video']))
const relativeVideoUrl = computed(() => {
  const value = task.value?.video_url
  if (!value) return ''
  try {
    const parsed = new URL(value, window.location.origin)
    if (parsed.pathname.startsWith('/storage/') || parsed.pathname.startsWith('/videos-pub/')) {
      return `${parsed.pathname}${parsed.search}${parsed.hash}`
    }
  } catch {
    return value
  }
  return value
})

async function load() {
  loading.value = true
  error.value = ''
  try { task.value = await getPublishedPost(postId) }
  catch (reason) { error.value = getErrorMessage(reason, t('publish.resultLoadFailed')) }
  finally { loading.value = false }
}

async function copyPostId() {
  try {
    await navigator.clipboard.writeText(task.value?.platform_post_id || postId)
    ElMessage.success(t('publish.postIdCopied'))
  } catch {
    ElMessage.error(t('publish.copyFailed'))
  }
}

onMounted(load)
</script>

<style scoped>
.delivery-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(310px, .72fr); gap: 20px; align-items: start; }
.delivery-stage { overflow: hidden; }
.delivery-stage-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; padding: 22px 24px; border-bottom: 1px solid var(--line-soft); }
.delivery-stage-head h2 { margin: 7px 0 0; color: var(--ink-950); font: 650 22px/1.15 "Bahnschrift SemiCondensed", "Microsoft YaHei UI", sans-serif; }
.stage-kicker { color: var(--blue-600); font: 650 10px/1.2 "Bahnschrift", sans-serif; letter-spacing: .12em; text-transform: uppercase; }
.player-frame { padding: 12px; background: var(--ink-950); }
.player-frame .video-player { display: block; width: 100%; max-height: 620px; border-radius: 8px; }
.player-empty { display: grid; min-height: 420px; place-items: center; align-content: center; gap: 12px; color: #95a2b6; }
.stage-foot { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 10px 24px; padding: 15px 22px; color: var(--ink-500); font-size: 11px; }
.receipt-card { position: relative; overflow: hidden; }
.receipt-signal { position: absolute; inset: 0 auto 0 0; width: 5px; background: var(--blue-600); }
.receipt-signal.is-success { background: var(--teal-500); }
.receipt-signal.is-failed { background: var(--danger); }
.receipt-signal.is-pending, .receipt-signal.is-publishing { background: var(--amber-500); }
.receipt-head { padding: 23px 24px 18px; border-bottom: 1px solid var(--line-soft); }
.receipt-head h2 { margin: 7px 0 0; font-size: 18px; }
.receipt-head p { margin: 7px 0 0; color: var(--ink-500); font-size: 11px; line-height: 1.65; }
.receipt-id-block { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 7px 10px; padding: 20px 24px; border-bottom: 1px solid var(--line-soft); background: #f8fafc; }
.receipt-id-block > span { grid-column: 1 / -1; color: var(--ink-500); font: 650 9px/1 "Bahnschrift", sans-serif; letter-spacing: .14em; text-transform: uppercase; }
.receipt-id-block strong { align-self: center; overflow-wrap: anywhere; color: var(--ink-950); font-size: 13px; }
.receipt-list { display: grid; grid-template-columns: 92px minmax(0, 1fr); row-gap: 13px; margin: 0; padding: 22px 24px; font-size: 12px; }
.receipt-list dt { color: var(--ink-500); }
.receipt-list dd { margin: 0; overflow-wrap: anywhere; color: var(--ink-800); }
.receipt-error { margin: 0 24px 24px; padding: 14px; border: 1px solid #f0cdd0; border-radius: 10px; background: #fff7f7; }
.receipt-error strong { color: var(--danger); font-size: 11px; }
.receipt-error p { margin: 7px 0 0; color: var(--ink-600); font-size: 11px; line-height: 1.65; }
@media (max-width: 980px) { .delivery-grid { grid-template-columns: 1fr; }.player-empty { min-height: 300px; } }
@media (max-width: 640px) { .delivery-stage-head { padding: 18px; }.stage-foot { padding: 14px 18px; }.receipt-list { grid-template-columns: 78px minmax(0, 1fr); }.player-frame { padding: 7px; } }
</style>
