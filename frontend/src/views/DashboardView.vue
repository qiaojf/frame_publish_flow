<template>
  <div>
    <PageHeader eyebrow="Overview" :title="`${greeting}，${auth.user?.display_name || auth.user?.username || '用户'}`" description="从生成到发布，查看今天需要关注的任务。">
      <template #actions><el-button @click="$router.push('/videos')">查看视频</el-button><el-button type="primary" @click="$router.push('/video/create')"><el-icon><Plus /></el-icon>制作视频</el-button></template>
    </PageHeader>

    <el-alert v-if="loadError" :title="loadError" type="warning" show-icon class="dashboard-alert" @close="loadError = ''" />
    <div class="metric-grid">
      <article v-for="metric in metrics" :key="metric.label" class="metric-card" :style="{ '--metric-color': metric.color }">
        <div class="label">{{ metric.label }}</div><div class="value">{{ metric.value }}</div><div class="hint">{{ metric.hint }}</div>
      </article>
    </div>

    <div class="dashboard-grid">
      <section class="surface">
        <div class="surface-header"><div><h2>最近生成视频</h2><p>最新完成或正在处理的视频资产</p></div><el-button text type="primary" @click="$router.push('/videos')">全部视频</el-button></div>
        <DataState :loading="loading" :empty="!videos.length" empty-text="还没有视频，先创建第一个生成任务" @retry="load">
          <el-button type="primary" @click="$router.push('/video/create')">制作视频</el-button>
          <template #content>
            <div class="strip-list">
              <button v-for="video in videos" :key="video.id" class="strip-item strip-button" @click="$router.push(`/videos/${video.id}`)">
                <div class="thumb"><img v-if="video.thumbnail_url" :src="video.thumbnail_url" alt="" /><VideoPlay v-else :size="20" /></div>
                <div><div class="item-title">{{ video.title }}</div><div class="item-meta">{{ video.model_name }} · {{ formatDate(video.created_at) }}</div></div>
                <StatusTag :status="video.generation_status ?? 'success'" />
              </button>
            </div>
          </template>
        </DataState>
      </section>

      <section class="surface">
        <div class="surface-header"><div><h2>最近发布记录</h2><p>每个平台任务独立记录</p></div><el-button text type="primary" @click="$router.push('/publish/history')">全部记录</el-button></div>
        <DataState :loading="loading" :empty="!tasks.length" empty-text="暂无发布记录" @retry="load">
          <template #content><div class="strip-list">
            <div v-for="task in tasks" :key="task.id" class="strip-item publish-strip">
              <div class="platform-glyph">{{ task.platform_name.slice(0, 1).toUpperCase() }}</div>
              <div><div class="item-title">{{ task.video_title || '未命名视频' }}</div><div class="item-meta">{{ task.platform_name }} · {{ task.account_name || '默认账号' }}</div></div>
              <StatusTag :status="task.status" />
            </div>
          </div></template>
        </DataState>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Plus, VideoPlay } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import DataState from '@/components/DataState.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useAuthStore } from '@/stores/auth'
import { getVideos } from '@/api/videos'
import { getGenerationTasks } from '@/api/generation'
import { getPublishTasks } from '@/api/publish'
import { getUsers } from '@/api/users'
import type { VideoAsset } from '@/types/video'
import type { GenerationTask } from '@/types/generation'
import type { PublishTask } from '@/types/publish'
import { formatDate } from '@/utils/format'

const auth = useAuthStore()
const loading = ref(true)
const loadError = ref('')
const videos = ref<VideoAsset[]>([])
const generationTasks = ref<GenerationTask[]>([])
const tasks = ref<PublishTask[]>([])
const userTotal = ref<number | null>(null)
const videoTotal = ref<number | null>(null)
const taskTotal = ref<number | null>(null)
const greeting = computed(() => { const hour = new Date().getHours(); return hour < 11 ? '早上好' : hour < 18 ? '下午好' : '晚上好' })
const today = new Date().toDateString()
const metrics = computed(() => {
  const base = [
    { label: auth.isAdmin ? '视频总数' : '我的视频', value: videoTotal.value ?? '—', hint: auth.isAdmin ? '系统内视频资产' : '当前账号的视频资产', color: '#2864dc' },
    { label: '今日生成任务', value: generationTasks.value.filter((item) => new Date(item.created_at).toDateString() === today).length, hint: '今日已提交', color: '#169a98' },
    { label: '生成中', value: generationTasks.value.filter((item) => ['pending', 'processing'].includes(item.status)).length, hint: '等待或处理中的任务', color: '#c47d16' },
    { label: '发布成功', value: tasks.value.filter((item) => item.status === 'success').length, hint: '最近记录', color: '#169a77' },
    { label: '发布失败', value: tasks.value.filter((item) => item.status === 'failed').length, hint: '需要人工关注', color: '#cf4c52' },
  ]
  if (auth.isAdmin) {
    base.push({ label: '用户总数', value: userTotal.value ?? '—', hint: '已配置系统用户', color: '#6d5bd0' })
    base.push({ label: '总任务数量', value: taskTotal.value ?? '—', hint: '生成任务总计', color: '#56708f' })
  }
  return base
})

async function load() {
  loading.value = true
  loadError.value = ''
  const results = await Promise.allSettled([
    getVideos({ page: 1, page_size: 5 }),
    getGenerationTasks({ page: 1, page_size: 50 }),
    getPublishTasks({ page: 1, page_size: 5 }),
    auth.isAdmin ? getUsers({ page: 1, page_size: 1 }) : Promise.resolve(null),
  ] as const)
  const [videoResult, generationResult, publishResult, usersResult] = results
  if (videoResult.status === 'fulfilled') { videos.value = videoResult.value.items; videoTotal.value = videoResult.value.total }
  if (generationResult.status === 'fulfilled') { generationTasks.value = generationResult.value.items; taskTotal.value = generationResult.value.total }
  if (publishResult.status === 'fulfilled') tasks.value = publishResult.value.items
  if (usersResult.status === 'fulfilled' && usersResult.value) userTotal.value = usersResult.value.total
  if (results.some((result) => result.status === 'rejected')) loadError.value = '部分数据未能加载，请确认后端服务与接口已就绪。'
  loading.value = false
}

onMounted(load)
</script>

<style scoped>
.dashboard-alert { margin-bottom: 16px; }
.strip-button { width: 100%; border: 0; background: transparent; text-align: left; cursor: pointer; }
.strip-button:hover { background: #f8faff; }
.publish-strip { grid-template-columns: 36px minmax(0, 1fr) auto; }
</style>
