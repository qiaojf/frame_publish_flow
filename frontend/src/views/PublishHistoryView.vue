<template>
  <div>
    <PageHeader :eyebrow="t('publish.historyEyebrow')" :title="t('publish.historyTitle')" :description="t('publish.historyIntro')">
      <template #actions><el-button type="primary" @click="$router.push('/publish')"><el-icon><Promotion /></el-icon>{{ t('publish.title') }}</el-button></template>
    </PageHeader>
    <section class="surface">
      <div class="toolbar"><div class="toolbar-group"><el-input v-model="filters.keyword" clearable :placeholder="t('publish.searchPlaceholder')" :prefix-icon="Search" style="width: 220px" @keyup.enter="applyFilters" @clear="applyFilters" /><el-select v-model="filters.platform_id" clearable :placeholder="t('publish.allPlatforms')" style="width: 150px" @change="applyFilters"><el-option v-for="platform in platforms" :key="platform.id" :label="platform.name" :value="platform.id" /></el-select><el-select v-model="filters.status" clearable :placeholder="t('publish.allStatuses')" style="width: 140px" @change="applyFilters"><el-option v-for="item in statuses" :key="item.value" :label="item.label" :value="item.value" /></el-select><el-date-picker v-model="filters.dates" type="daterange" value-format="YYYY-MM-DD" :start-placeholder="t('publish.startDate')" :end-placeholder="t('publish.endDate')" :range-separator="t('publish.rangeSeparator')" @change="applyFilters" /></div><span class="muted">{{ t('publish.totalRecords', { count: total }) }}</span></div>
      <DataState :loading="loading" :error="error" :empty="!tasks.length" :empty-text="t('publish.noRecords')" @retry="load">
        <template #content>
          <el-table :data="tasks" style="width: 100%">
            <el-table-column :label="t('common.video')" min-width="220"><template #default="scope"><div class="table-video"><div class="thumb"><img v-if="scope.row.video_thumbnail_url" :src="scope.row.video_thumbnail_url" alt="" /><VideoPlay v-else :size="16" /></div><div><div class="item-title">{{ scope.row.video_title || t('common.untitledVideo') }}</div><button class="link-button" @click="$router.push(`/videos/${scope.row.video_id}`)">{{ t('publish.viewVideo') }}</button></div></div></template></el-table-column>
            <el-table-column prop="platform_name" :label="t('common.platform')" width="130" />
            <el-table-column :label="t('publish.publishAccountColumn')" min-width="140"><template #default="scope">{{ scope.row.account_name || t('common.defaultAccount') }}</template></el-table-column>
            <el-table-column :label="t('common.status')" width="110"><template #default="scope"><StatusTag :status="scope.row.status" /></template></el-table-column>
            <el-table-column :label="t('publish.publishTime')" min-width="165"><template #default="scope">{{ formatDate(scope.row.published_at || scope.row.created_at) }}</template></el-table-column>
            <el-table-column :label="t('common.result')" min-width="240"><template #default="scope"><div v-if="scope.row.publish_url || scope.row.platform_url" class="result-links"><button v-if="isInternalUrl(scope.row.publish_url)" class="link-button" @click="$router.push(scope.row.publish_url)">{{ t('publish.viewPublishedContent') }}<el-icon><TopRight /></el-icon></button><a v-else-if="scope.row.publish_url" class="link-button" :href="scope.row.publish_url" target="_blank" rel="noopener">{{ t('publish.viewPublishedContent') }}<el-icon><TopRight /></el-icon></a><a v-if="scope.row.platform_url" class="link-button" :href="scope.row.platform_url" target="_blank" rel="noopener">{{ t('publish.openPlatformHome') }}<el-icon><TopRight /></el-icon></a></div><span v-else-if="scope.row.error_message" class="error-cell">{{ getBusinessErrorMessage(scope.row.error_code, scope.row.error_message) }}</span><span v-else>—</span></template></el-table-column>
            <el-table-column :label="t('common.actions')" width="110" fixed="right"><template #default="scope"><el-button v-if="scope.row.status === 'failed'" text type="primary" :loading="retryingId === scope.row.id" @click="retry(scope.row)">{{ t('publish.republish') }}</el-button><span v-else>—</span></template></el-table-column>
          </el-table>
        </template>
      </DataState>
      <div v-if="total > pageSize" class="pagination-row"><el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="load" /></div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
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
import { getBusinessErrorMessage, getErrorMessage } from '@/utils/errors'

const tasks = ref<PublishTask[]>([]); const platforms = ref<PublishPlatform[]>([]); const loading = ref(true); const error = ref(''); const retryingId = ref('')
const { t } = useI18n()
const page = ref(1); const pageSize = 20; const total = ref(0)
const filters = reactive<{ keyword: string; platform_id: string; status: string; dates: string[] }>({ keyword: '', platform_id: '', status: '', dates: [] })
const statuses = computed(() => ['pending', 'publishing', 'success', 'failed', 'cancelled'].map((value) => ({ label: t(`status.${value}`), value })))
const pollInterval = Number(import.meta.env.VITE_POLL_INTERVAL_MS ?? 4000); let pollTimer: number | undefined

async function load() {
  loading.value = true; error.value = ''
  try { const result = await getPublishTasks({ page: page.value, page_size: pageSize, keyword: filters.keyword || undefined, platform_id: filters.platform_id || undefined, status: filters.status || undefined, date_from: filters.dates[0], date_to: filters.dates[1] }); tasks.value = result.items; total.value = result.total }
  catch (reason) { error.value = getErrorMessage(reason, t('publish.historyLoadFailed')) }
  finally { loading.value = false; schedulePoll() }
}
function schedulePoll() { window.clearTimeout(pollTimer); if (tasks.value.some((task) => ['pending', 'publishing'].includes(task.status))) pollTimer = window.setTimeout(load, pollInterval) }
function applyFilters() { page.value = 1; load() }
function isInternalUrl(value?: string) { return Boolean(value?.startsWith('/')) }
async function retry(task: PublishTask) {
  retryingId.value = task.id
  try { await retryPublishTask(task.id); ElMessage.success(t('publish.retryCreated', { platform: task.platform_name })); await load() }
  catch (reason) { ElMessage.error(getErrorMessage(reason, t('publish.retryFailed'))) }
  finally { retryingId.value = '' }
}
onMounted(async () => { getPublishPlatforms().then((items) => { platforms.value = items }).catch(() => undefined); await load() })
onBeforeUnmount(() => window.clearTimeout(pollTimer))
</script>

<style scoped>
.table-video { display: grid; grid-template-columns: 58px minmax(0, 1fr); gap: 12px; align-items: center; }
.error-cell { display: -webkit-box; overflow: hidden; color: var(--danger); -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.link-button .el-icon { margin-left: 4px; vertical-align: -2px; }
.result-links { display: flex; flex-wrap: wrap; gap: 8px 14px; }
</style>
