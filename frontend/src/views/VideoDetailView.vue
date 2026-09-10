<template>
  <div>
    <PageHeader eyebrow="Asset detail" :title="video?.title || '视频详情'" description="查看生成参数、视频文件与平台发布历史。">
      <template #actions><el-button @click="$router.push('/videos')">返回列表</el-button><template v-if="video"><el-button @click="download">下载</el-button><el-button type="primary" @click="$router.push({ path: '/publish', query: { video: video.id } })">发布视频</el-button></template></template>
    </PageHeader>
    <DataState :loading="loading" :error="error" :empty="!video" empty-text="视频不存在或已被删除" @retry="load">
      <template #content>
        <div v-if="video" class="content-grid">
          <div>
            <section class="surface player-surface"><video v-if="video.video_url" class="video-player" :src="video.video_url" controls preload="metadata" :poster="video.thumbnail_url">浏览器不支持视频播放。</video><div v-else class="player-empty"><VideoPlay :size="34" /><span>视频文件尚未就绪</span></div></section>
            <section class="surface publish-history">
              <div class="surface-header"><div><h2>发布历史</h2><p>每个平台作为独立任务展示</p></div></div>
              <DataState :loading="historyLoading" :empty="!history.length" empty-text="这个视频还没有发布记录">
                <template #content><el-table :data="history"><el-table-column prop="platform_name" label="平台" /><el-table-column prop="account_name" label="账号" /><el-table-column label="状态"><template #default="scope"><StatusTag :status="scope.row.status" /></template></el-table-column><el-table-column label="时间" min-width="150"><template #default="scope">{{ formatDate(scope.row.published_at || scope.row.created_at) }}</template></el-table-column><el-table-column label="结果"><template #default="scope"><a v-if="scope.row.publish_url" class="link-button" :href="scope.row.publish_url" target="_blank" rel="noopener">打开链接</a><span v-else-if="scope.row.error_message" class="danger-text">{{ scope.row.error_message }}</span><span v-else>—</span></template></el-table-column></el-table></template>
              </DataState>
            </section>
          </div>
          <aside class="surface"><div class="surface-header"><div><h2>生成信息</h2><p>提交给后端的生成依据</p></div><StatusTag :status="video.generation_status ?? 'success'" /></div><div class="surface-body"><dl class="detail-list"><dt>Prompt</dt><dd>{{ video.prompt }}</dd><dt>生成方式</dt><dd>{{ video.generation_type === 'image_to_video' ? '图生视频' : '文生视频' }}</dd><dt>视频模型</dt><dd>{{ video.model_name }}</dd><dt>时长</dt><dd>{{ video.duration ? `${video.duration} 秒` : '—' }}</dd><dt>分辨率</dt><dd>{{ video.resolution || '—' }}</dd><dt>画面比例</dt><dd>{{ video.aspect_ratio || '—' }}</dd><dt>视频尺寸</dt><dd>{{ video.width && video.height ? `${video.width} × ${video.height}` : '—' }}</dd><dt>文件大小</dt><dd>{{ formatBytes(video.file_size) }}</dd><dt>创建时间</dt><dd>{{ formatDate(video.created_at) }}</dd><template v-if="video.reference_image_url"><dt>参考图片</dt><dd><img class="reference-image" :src="video.reference_image_url" alt="生成视频使用的参考图片" /></dd></template></dl><div class="detail-actions"><el-button @click="$router.push({ path: '/video/create', query: { regenerate: video.id } })">重新生成</el-button><el-button type="danger" plain @click="remove">删除视频</el-button></div></div></aside>
        </div>
      </template>
    </DataState>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
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
import { getErrorMessage } from '@/utils/errors'

const route = useRoute(); const router = useRouter(); const id = String(route.params.id)
const video = ref<VideoAsset>(); const history = ref<PublishTask[]>([]); const loading = ref(true); const historyLoading = ref(true); const error = ref('')
async function load() {
  loading.value = true; error.value = ''
  try { video.value = await getVideo(id); loading.value = false; await loadHistory() }
  catch (reason) { error.value = getErrorMessage(reason, '视频详情加载失败'); loading.value = false; historyLoading.value = false }
}
async function loadHistory() { historyLoading.value = true; try { history.value = (await getPublishTasks({ page: 1, page_size: 50, video_id: id })).items } catch { history.value = [] } finally { historyLoading.value = false } }
async function download() {
  if (!video.value) return
  try { const response = await downloadVideo(video.value.id); const url = URL.createObjectURL(response.data); const anchor = document.createElement('a'); anchor.href = url; anchor.download = pickFilename(response.headers['content-disposition'], `${video.value.title}.mp4`); anchor.click(); URL.revokeObjectURL(url) }
  catch (reason) { ElMessage.error(getErrorMessage(reason, '视频下载失败')) }
}
async function remove() {
  if (!video.value) return
  try { await ElMessageBox.confirm(`删除“${video.value.title}”后无法恢复，是否继续？`, '删除视频', { type: 'warning', confirmButtonText: '确认删除' }); await deleteVideo(video.value.id); ElMessage.success('视频已删除'); router.replace('/videos') }
  catch (reason) { if (reason !== 'cancel' && reason !== 'close') ElMessage.error(getErrorMessage(reason, '删除失败')) }
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
