<template>
  <div>
    <PageHeader :eyebrow="t('video.detailEyebrow')" :title="video?.title || t('routes.videoDetail')" :description="t('video.detailIntro')">
      <template #actions><el-button @click="$router.push('/videos')">{{ t('video.backToList') }}</el-button><template v-if="video"><el-button @click="download">{{ t('common.download') }}</el-button><el-button type="primary" @click="$router.push({ path: '/publish', query: { video: video.id } })">{{ t('routes.publish') }}</el-button></template></template>
    </PageHeader>
    <DataState :loading="loading" :error="error" :empty="!video" :empty-text="t('video.notFound')" @retry="load">
      <template #content>
        <div v-if="video" class="content-grid">
          <div>
            <section class="surface player-surface"><video v-if="video.video_url" class="video-player" :src="video.video_url" controls preload="metadata" :poster="video.thumbnail_url">{{ t('video.browserUnsupported') }}</video><div v-else class="player-empty"><VideoPlay :size="34" /><span>{{ t('video.fileNotReady') }}</span></div></section>
            <section class="surface publish-history">
              <div class="surface-header"><div><h2>{{ t('video.publishHistory') }}</h2><p>{{ t('video.publishHistoryHint') }}</p></div></div>
              <DataState :loading="historyLoading" :empty="!history.length" :empty-text="t('video.noPublishHistory')">
                <template #content><el-table :data="history"><el-table-column prop="platform_name" :label="t('common.platform')" /><el-table-column prop="account_name" :label="t('common.account')" /><el-table-column :label="t('common.status')"><template #default="scope"><StatusTag :status="scope.row.status" /></template></el-table-column><el-table-column :label="t('common.time')" min-width="150"><template #default="scope">{{ formatDate(scope.row.published_at || scope.row.created_at) }}</template></el-table-column><el-table-column :label="t('common.result')"><template #default="scope"><a v-if="cleanUrl(scope.row.publish_url)" class="link-button" :href="cleanUrl(scope.row.publish_url)" target="_blank" rel="noopener">{{ t('video.openLink') }}</a><span v-else-if="scope.row.error_message" class="danger-text">{{ getBusinessErrorMessage(scope.row.error_code, scope.row.error_message) }}</span><span v-else>—</span></template></el-table-column></el-table></template>
              </DataState>
            </section>
          </div>
          <aside class="surface"><div class="surface-header"><div><h2>{{ t('video.generationInfo') }}</h2><p>{{ t('video.generationInfoHint') }}</p></div><StatusTag :status="video.generation_status ?? 'success'" /></div><div class="surface-body"><dl class="detail-list"><dt>{{ t('common.prompt') }}</dt><dd>{{ video.prompt }}</dd><dt>{{ t('video.generationMethod') }}</dt><dd>{{ t(`generationType.${video.generation_type}`) }}</dd><dt>{{ t('video.model') }}</dt><dd>{{ video.model_name }}</dd><dt>{{ t('video.duration') }}</dt><dd>{{ video.duration ? t('common.seconds', { count: video.duration }) : '—' }}</dd><dt>{{ t('video.resolution') }}</dt><dd>{{ video.resolution || '—' }}</dd><dt>{{ t('video.aspectRatio') }}</dt><dd>{{ video.aspect_ratio || '—' }}</dd><dt>{{ t('video.dimensions') }}</dt><dd>{{ video.width && video.height ? `${video.width} × ${video.height}` : '—' }}</dd><dt>{{ t('video.fileSize') }}</dt><dd>{{ formatBytes(video.file_size) }}</dd><dt>{{ t('video.createdAt') }}</dt><dd>{{ formatDate(video.created_at) }}</dd><template v-if="video.reference_image_url"><dt>{{ t('video.referenceImage') }}</dt><dd><img class="reference-image" :src="video.reference_image_url" :alt="t('video.referenceAlt')" /></dd></template></dl><div class="detail-actions"><el-button @click="$router.push({ path: '/video/create', query: { regenerate: video.id } })">{{ t('video.regenerate') }}</el-button><el-button type="danger" plain @click="remove">{{ t('video.deleteTitle') }}</el-button></div></div></aside>
        </div>
      </template>
    </DataState>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { VideoPlay } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import DataState from '@/components/DataState.vue'
import StatusTag from '@/components/StatusTag.vue'
import { deleteVideo, downloadVideo, getVideo } from '@/api/videos'
import { getPublishTasks } from '@/api/publish'
import type { VideoAsset } from '@/types/video'
import type { PublishTask } from '@/types/publish'
import { formatBytes, formatDate, pickFilename } from '@/utils/format'
import { getBusinessErrorMessage, getErrorMessage } from '@/utils/errors'
import { cleanUrl } from '@/utils/url'

const route = useRoute(); const router = useRouter(); const id = String(route.params.id)
const { t } = useI18n()
const video = ref<VideoAsset>(); const history = ref<PublishTask[]>([]); const loading = ref(true); const historyLoading = ref(true); const error = ref('')
async function load() {
  loading.value = true; error.value = ''
  try { video.value = await getVideo(id); loading.value = false; await loadHistory() }
  catch (reason) { error.value = getErrorMessage(reason, t('video.detailLoadFailed')); loading.value = false; historyLoading.value = false }
}
async function loadHistory() { historyLoading.value = true; try { history.value = (await getPublishTasks({ page: 1, page_size: 50, video_id: id })).items } catch { history.value = [] } finally { historyLoading.value = false } }
async function download() {
  if (!video.value) return
  try { const response = await downloadVideo(video.value.id); const url = URL.createObjectURL(response.data); const anchor = document.createElement('a'); anchor.href = url; anchor.download = pickFilename(response.headers['content-disposition'], `${video.value.title}.mp4`); anchor.click(); URL.revokeObjectURL(url) }
  catch (reason) { ElMessage.error(getErrorMessage(reason, t('video.downloadFailed'))) }
}
async function remove() {
  if (!video.value) return
  try { await ElMessageBox.confirm(t('video.deleteConfirm', { title: video.value.title }), t('video.deleteTitle'), { type: 'warning', confirmButtonText: t('common.confirmDelete'), cancelButtonText: t('common.cancel') }); await deleteVideo(video.value.id); ElMessage.success(t('video.deleted')); router.replace('/videos') }
  catch (reason) { if (reason !== 'cancel' && reason !== 'close') ElMessage.error(getErrorMessage(reason, t('video.deleteFailed'))) }
}
onMounted(load)
</script>

<style scoped>
.player-surface { padding: 12px; background: var(--ink-950); }
.player-empty { display: grid; min-height: 360px; place-items: center; align-content: center; gap: 10px; color: #8e9bb0; }
.publish-history { margin-top: 20px; }
.reference-image { display: block; width: min(100%, 190px); max-height: 150px; border-radius: 8px; object-fit: cover; }
.detail-actions { display: flex; gap: 10px; margin-top: 24px; padding-top: 18px; border-top: 1px solid var(--line-soft); }
</style>
