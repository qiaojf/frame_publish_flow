<template>
  <div>
    <PageHeader eyebrow="Library" title="我的视频" description="管理生成的视频资产，并从这里继续预览、下载或发布。">
      <template #actions><el-button type="primary" @click="$router.push('/video/create')"><el-icon><Plus /></el-icon>制作视频</el-button></template>
    </PageHeader>
    <section class="surface">
      <div class="toolbar">
        <div class="toolbar-group">
          <el-input v-model="filters.keyword" clearable placeholder="搜索标题或描述" :prefix-icon="Search" style="width: 240px" @keyup.enter="applyFilters" @clear="applyFilters" />
          <el-select v-model="filters.status" clearable placeholder="生成状态" style="width: 150px" @change="applyFilters">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button @click="applyFilters">筛选</el-button>
        </div>
        <div class="toolbar-group"><span class="muted">共 {{ total }} 个视频</span><el-radio-group v-model="viewMode" size="small"><el-radio-button value="card">卡片</el-radio-button><el-radio-button value="table">列表</el-radio-button></el-radio-group></div>
      </div>
      <DataState :loading="loading" :error="error" :empty="!videos.length" empty-text="没有找到符合条件的视频" @retry="load">
        <el-button type="primary" @click="$router.push('/video/create')">制作第一个视频</el-button>
        <template #content>
          <div v-if="viewMode === 'card'" class="video-card-grid">
            <article v-for="video in videos" :key="video.id" class="video-card">
              <button class="thumb video-thumb-button" type="button" @click="$router.push(`/videos/${video.id}`)"><img v-if="video.thumbnail_url" :src="video.thumbnail_url" :alt="video.title" /><VideoPlay v-else :size="28" /></button>
              <div class="video-card-content"><h3>{{ video.title }}</h3><div class="video-card-meta"><span>{{ generationType(video.generation_type) }} · {{ video.model_name }}</span><span>{{ video.duration ? `${video.duration}s` : '—' }}</span></div><div class="video-card-actions"><StatusTag :status="video.generation_status ?? 'success'" /><el-dropdown @command="(command: string) => handleAction(command, video)"><el-button text type="primary">操作<el-icon><ArrowDown /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="detail">查看详情</el-dropdown-item><el-dropdown-item command="download">下载</el-dropdown-item><el-dropdown-item command="publish">发布</el-dropdown-item><el-dropdown-item command="regenerate">重新生成</el-dropdown-item><el-dropdown-item divided command="delete">删除</el-dropdown-item></el-dropdown-menu></template></el-dropdown></div></div>
            </article>
          </div>
          <el-table v-else :data="videos" style="width: 100%">
            <el-table-column label="视频" min-width="240"><template #default="scope"><div class="table-video"><div class="thumb"><img v-if="scope.row.thumbnail_url" :src="scope.row.thumbnail_url" alt="" /><VideoPlay v-else :size="16" /></div><div><div class="item-title">{{ scope.row.title }}</div><div class="item-meta">{{ scope.row.model_name }}</div></div></div></template></el-table-column>
            <el-table-column label="生成方式" width="110"><template #default="scope">{{ generationType(scope.row.generation_type) }}</template></el-table-column>
            <el-table-column label="时长" width="90"><template #default="scope">{{ scope.row.duration ? `${scope.row.duration}s` : '—' }}</template></el-table-column>
            <el-table-column label="生成状态" width="120"><template #default="scope"><StatusTag :status="scope.row.generation_status ?? 'success'" /></template></el-table-column>
            <el-table-column label="发布时间" min-width="160"><template #default="scope">{{ formatDate(scope.row.created_at) }}</template></el-table-column>
            <el-table-column label="操作" width="210" fixed="right"><template #default="scope"><el-button text type="primary" @click="handleAction('detail', scope.row)">详情</el-button><el-button text type="primary" @click="handleAction('publish', scope.row)">发布</el-button><el-button text type="danger" @click="handleAction('delete', scope.row)">删除</el-button></template></el-table-column>
          </el-table>
        </template>
      </DataState>
      <div v-if="total > pageSize" class="pagination-row"><el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="load" /></div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
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
const loading = ref(true)
const error = ref('')
const videos = ref<VideoAsset[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const viewMode = ref<'card' | 'table'>('card')
const filters = reactive({ keyword: '', status: '' })
const statusOptions = [{ label: '等待中', value: 'pending' }, { label: '生成中', value: 'processing' }, { label: '成功', value: 'success' }, { label: '失败', value: 'failed' }]
const generationType = (type: VideoAsset['generation_type']) => type === 'image_to_video' ? '图生视频' : '文生视频'

async function load() {
  loading.value = true; error.value = ''
  try { const result = await getVideos({ page: page.value, page_size: pageSize, keyword: filters.keyword || undefined, status: filters.status || undefined }); videos.value = result.items; total.value = result.total }
  catch (reason) { error.value = getErrorMessage(reason, '视频列表加载失败') }
  finally { loading.value = false }
}

function applyFilters() { page.value = 1; load() }
async function saveDownload(video: VideoAsset) {
  try {
    const response = await downloadVideo(video.id)
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = pickFilename(response.headers['content-disposition'], `${video.title}.mp4`); anchor.click(); URL.revokeObjectURL(url)
  } catch (reason) { ElMessage.error(getErrorMessage(reason, '视频下载失败')) }
}
async function remove(video: VideoAsset) {
  try {
    await ElMessageBox.confirm(`删除“${video.title}”后无法恢复，是否继续？`, '删除视频', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' })
    await deleteVideo(video.id); ElMessage.success('视频已删除'); await load()
  } catch (reason) { if (reason !== 'cancel' && reason !== 'close') ElMessage.error(getErrorMessage(reason, '删除失败')) }
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
