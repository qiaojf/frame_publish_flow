<template>
  <div>
    <PageHeader :eyebrow="t('video.libraryEyebrow')" :title="t('video.libraryTitle')" :description="t('video.libraryIntro')">
      <template #actions><el-button type="primary" @click="$router.push('/video/create')"><el-icon><Plus /></el-icon>{{ t('video.createTitle') }}</el-button></template>
    </PageHeader>
    <section class="surface">
      <div class="toolbar">
        <div class="toolbar-group">
          <el-input v-model="filters.keyword" clearable :placeholder="t('video.searchPlaceholder')" :prefix-icon="Search" style="width: 240px" @keyup.enter="applyFilters" @clear="applyFilters" />
          <el-select v-model="filters.status" clearable :placeholder="t('video.generationStatus')" style="width: 150px" @change="applyFilters">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button @click="applyFilters">{{ t('common.filter') }}</el-button>
        </div>
        <div class="toolbar-group"><span class="muted">{{ t('video.totalVideos', { count: total }) }}</span><el-radio-group v-model="viewMode" size="small"><el-radio-button value="card">{{ t('video.card') }}</el-radio-button><el-radio-button value="table">{{ t('video.list') }}</el-radio-button></el-radio-group></div>
      </div>
      <DataState :loading="loading" :error="error" :empty="!videos.length" :empty-text="t('video.noMatches')" @retry="load">
        <el-button type="primary" @click="$router.push('/video/create')">{{ t('video.createFirst') }}</el-button>
        <template #content>
          <div v-if="viewMode === 'card'" class="video-card-grid">
            <article v-for="video in videos" :key="video.id" class="video-card">
              <button class="thumb video-thumb-button" type="button" @click="$router.push(`/videos/${video.id}`)"><img v-if="video.thumbnail_url" :src="video.thumbnail_url" :alt="video.title" /><VideoPlay v-else :size="28" /></button>
              <div class="video-card-content"><h3>{{ video.title }}</h3><div class="video-card-meta"><span>{{ generationType(video.generation_type) }} · {{ video.model_name }}</span><span>{{ video.duration ? t('common.seconds', { count: video.duration }) : '—' }}</span></div><div class="video-card-actions"><StatusTag :status="video.generation_status ?? 'success'" /><el-dropdown @command="(command: string) => handleAction(command, video)"><el-button text type="primary">{{ t('common.actions') }}<el-icon><ArrowDown /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="detail">{{ t('video.viewDetail') }}</el-dropdown-item><el-dropdown-item command="download">{{ t('common.download') }}</el-dropdown-item><el-dropdown-item command="publish">{{ t('common.publish') }}</el-dropdown-item><el-dropdown-item command="regenerate">{{ t('video.regenerate') }}</el-dropdown-item><el-dropdown-item divided command="delete">{{ t('common.delete') }}</el-dropdown-item></el-dropdown-menu></template></el-dropdown></div></div>
            </article>
          </div>
          <el-table v-else :data="videos" style="width: 100%">
            <el-table-column :label="t('common.video')" min-width="240"><template #default="scope"><div class="table-video"><div class="thumb"><img v-if="scope.row.thumbnail_url" :src="scope.row.thumbnail_url" alt="" /><VideoPlay v-else :size="16" /></div><div><div class="item-title">{{ scope.row.title }}</div><div class="item-meta">{{ scope.row.model_name }}</div></div></div></template></el-table-column>
            <el-table-column :label="t('video.generationMethod')" width="120"><template #default="scope">{{ generationType(scope.row.generation_type) }}</template></el-table-column>
            <el-table-column :label="t('video.duration')" width="100"><template #default="scope">{{ scope.row.duration ? t('common.seconds', { count: scope.row.duration }) : '—' }}</template></el-table-column>
            <el-table-column :label="t('video.generationStatus')" width="130"><template #default="scope"><StatusTag :status="scope.row.generation_status ?? 'success'" /></template></el-table-column>
            <el-table-column :label="t('video.createdAt')" min-width="160"><template #default="scope">{{ formatDate(scope.row.created_at) }}</template></el-table-column>
            <el-table-column :label="t('common.actions')" width="210" fixed="right"><template #default="scope"><el-button text type="primary" @click="handleAction('detail', scope.row)">{{ t('common.details') }}</el-button><el-button text type="primary" @click="handleAction('publish', scope.row)">{{ t('common.publish') }}</el-button><el-button text type="danger" @click="handleAction('delete', scope.row)">{{ t('common.delete') }}</el-button></template></el-table-column>
          </el-table>
        </template>
      </DataState>
      <div v-if="total > pageSize" class="pagination-row"><el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="load" /></div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ArrowDown, Plus, Search, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import DataState from '@/components/DataState.vue'
import StatusTag from '@/components/StatusTag.vue'
import { deleteVideo, downloadVideo, getVideos } from '@/api/videos'
import type { VideoAsset } from '@/types/video'
import { formatDate, pickFilename } from '@/utils/format'
import { getErrorMessage } from '@/utils/errors'

const router = useRouter()
const { t } = useI18n()
const loading = ref(true)
const error = ref('')
const videos = ref<VideoAsset[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const viewMode = ref<'card' | 'table'>('card')
const filters = reactive({ keyword: '', status: '' })
const statusOptions = computed(() => ['pending', 'processing', 'success', 'failed'].map((value) => ({ label: t(`status.${value}`), value })))
const generationType = (type: VideoAsset['generation_type']) => t(`generationType.${type}`)

async function load() {
  loading.value = true; error.value = ''
  try { const result = await getVideos({ page: page.value, page_size: pageSize, keyword: filters.keyword || undefined, status: filters.status || undefined }); videos.value = result.items; total.value = result.total }
  catch (reason) { error.value = getErrorMessage(reason, t('video.listLoadFailed')) }
  finally { loading.value = false }
}

function applyFilters() { page.value = 1; load() }
async function saveDownload(video: VideoAsset) {
  try {
    const response = await downloadVideo(video.id)
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = pickFilename(response.headers['content-disposition'], `${video.title}.mp4`); anchor.click(); URL.revokeObjectURL(url)
  } catch (reason) { ElMessage.error(getErrorMessage(reason, t('video.downloadFailed'))) }
}
async function remove(video: VideoAsset) {
  try {
    await ElMessageBox.confirm(t('video.deleteConfirm', { title: video.title }), t('video.deleteTitle'), { type: 'warning', confirmButtonText: t('common.confirmDelete'), cancelButtonText: t('common.cancel') })
    await deleteVideo(video.id); ElMessage.success(t('video.deleted')); await load()
  } catch (reason) { if (reason !== 'cancel' && reason !== 'close') ElMessage.error(getErrorMessage(reason, t('video.deleteFailed'))) }
}
function handleAction(command: string, video: VideoAsset) {
  if (command === 'detail') router.push(`/videos/${video.id}`)
  else if (command === 'publish') router.push({ path: '/publish', query: { video: video.id } })
  else if (command === 'regenerate') router.push({ path: '/video/create', query: { regenerate: video.id } })
  else if (command === 'download') saveDownload(video)
  else if (command === 'delete') remove(video)
}
onMounted(load)
</script>

<style scoped>
.video-thumb-button { width: 100%; border: 0; cursor: pointer; }
.table-video { display: grid; grid-template-columns: 58px minmax(0, 1fr); gap: 12px; align-items: center; }
</style>
