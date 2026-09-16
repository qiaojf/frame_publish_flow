<template>
  <div>
    <PageHeader eyebrow="Delivery log" title="发布记录" description="按平台查看每一个独立任务的状态、回执与失败原因。">
      <template #actions><el-button type="primary" @click="$router.push('/publish')"><el-icon><Promotion /></el-icon>发布视频</el-button></template>
    </PageHeader>
    <section class="surface">
      <div class="toolbar"><div class="toolbar-group"><el-input v-model="filters.keyword" clearable placeholder="搜索视频或账号" :prefix-icon="Search" style="width: 220px" @keyup.enter="applyFilters" @clear="applyFilters" /><el-select v-model="filters.platform_id" clearable placeholder="全部平台" style="width: 150px" @change="applyFilters"><el-option v-for="platform in platforms" :key="platform.id" :label="platform.name" :value="platform.id" /></el-select><el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 140px" @change="applyFilters"><el-option v-for="item in statuses" :key="item.value" :label="item.label" :value="item.value" /></el-select><el-date-picker v-model="filters.dates" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" range-separator="至" @change="applyFilters" /></div><span class="muted">共 {{ total }} 条记录</span></div>
      <DataState :loading="loading" :error="error" :empty="!tasks.length" empty-text="没有符合筛选条件的发布记录" @retry="load">
        <template #content>
          <el-table :data="tasks" style="width: 100%">
            <el-table-column label="视频" min-width="220"><template #default="scope"><div class="table-video"><div class="thumb"><img v-if="scope.row.video_thumbnail_url" :src="scope.row.video_thumbnail_url" alt="" /><VideoPlay v-else :size="16" /></div><div><div class="item-title">{{ scope.row.video_title || '未命名视频' }}</div><button class="link-button" @click="$router.push(`/videos/${scope.row.video_id}`)">查看视频</button></div></div></template></el-table-column>
            <el-table-column prop="platform_name" label="平台" width="130" />
            <el-table-column label="发布账号" min-width="140"><template #default="scope">{{ scope.row.account_name || '默认账号' }}</template></el-table-column>
            <el-table-column label="状态" width="110"><template #default="scope"><StatusTag :status="scope.row.status" /></template></el-table-column>
            <el-table-column label="发布时间" min-width="165"><template #default="scope">{{ formatDate(scope.row.published_at || scope.row.created_at) }}</template></el-table-column>
            <el-table-column label="结果" min-width="220"><template #default="scope"><button v-if="isInternalUrl(scope.row.publish_url)" class="link-button" @click="$router.push(scope.row.publish_url)">打开发布页面<el-icon><TopRight /></el-icon></button><a v-else-if="scope.row.publish_url" class="link-button" :href="scope.row.publish_url" target="_blank" rel="noopener">打开平台页面<el-icon><TopRight /></el-icon></a><span v-else-if="scope.row.error_message" class="error-cell">{{ scope.row.error_message }}</span><span v-else>—</span></template></el-table-column>
            <el-table-column label="操作" width="110" fixed="right"><template #default="scope"><el-button v-if="scope.row.status === 'failed'" text type="primary" :loading="retryingId === scope.row.id" @click="retry(scope.row)">重新发布</el-button><span v-else>—</span></template></el-table-column>
          </el-table>
        </template>
      </DataState>
      <div v-if="total > pageSize" class="pagination-row"><el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="load" /></div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { Promotion, Search, TopRight, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import DataState from '@/components/DataState.vue'
import StatusTag from '@/components/StatusTag.vue'
import { getPublishTasks, retryPublishTask } from '@/api/publish'
import { getPublishPlatforms } from '@/api/platforms'
import type { PublishTask } from '@/types/publish'
import type { PublishPlatform } from '@/types/platform'
import { formatDate } from '@/utils/format'
import { getErrorMessage } from '@/utils/errors'

const tasks = ref<PublishTask[]>([]); const platforms = ref<PublishPlatform[]>([]); const loading = ref(true); const error = ref(''); const retryingId = ref('')
const page = ref(1); const pageSize = 20; const total = ref(0)
const filters = reactive<{ keyword: string; platform_id: string; status: string; dates: string[] }>({ keyword: '', platform_id: '', status: '', dates: [] })
const statuses = [{ label: '等待中', value: 'pending' }, { label: '发布中', value: 'publishing' }, { label: '成功', value: 'success' }, { label: '失败', value: 'failed' }, { label: '已取消', value: 'cancelled' }]
const pollInterval = Number(import.meta.env.VITE_POLL_INTERVAL_MS ?? 4000); let pollTimer: number | undefined

async function load() {
  loading.value = true; error.value = ''
  try { const result = await getPublishTasks({ page: page.value, page_size: pageSize, keyword: filters.keyword || undefined, platform_id: filters.platform_id || undefined, status: filters.status || undefined, date_from: filters.dates[0], date_to: filters.dates[1] }); tasks.value = result.items; total.value = result.total }
  catch (reason) { error.value = getErrorMessage(reason, '发布记录加载失败') }
  finally { loading.value = false; schedulePoll() }
}
function schedulePoll() { window.clearTimeout(pollTimer); if (tasks.value.some((task) => ['pending', 'publishing'].includes(task.status))) pollTimer = window.setTimeout(load, pollInterval) }
function applyFilters() { page.value = 1; load() }
function isInternalUrl(value?: string) { return Boolean(value?.startsWith('/')) }
async function retry(task: PublishTask) {
  retryingId.value = task.id
  try { await retryPublishTask(task.id); ElMessage.success(`已为 ${task.platform_name} 创建重试任务`); await load() }
  catch (reason) { ElMessage.error(getErrorMessage(reason, '重新发布失败')) }
  finally { retryingId.value = '' }
}
onMounted(async () => { getPublishPlatforms().then((items) => { platforms.value = items }).catch(() => undefined); await load() })
onBeforeUnmount(() => window.clearTimeout(pollTimer))
</script>

<style scoped>
.table-video { display: grid; grid-template-columns: 58px minmax(0, 1fr); gap: 12px; align-items: center; }
.error-cell { display: -webkit-box; overflow: hidden; color: var(--danger); -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.link-button .el-icon { margin-left: 4px; vertical-align: -2px; }
</style>
