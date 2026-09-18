<template>
  <div>
    <PageHeader :eyebrow="t('dashboard.eyebrow')" :title="t('dashboard.greeting', { greeting, name: auth.user?.display_name || auth.user?.username || t('common.user') })" :description="t('dashboard.intro')">
      <template #actions><el-button @click="$router.push('/videos')">{{ t('dashboard.viewVideos') }}</el-button><el-button type="primary" @click="$router.push('/video/create')"><el-icon><Plus /></el-icon>{{ t('dashboard.createVideo') }}</el-button></template>
    </PageHeader>

    <el-alert v-if="loadError" :title="loadError" type="warning" show-icon class="dashboard-alert" @close="loadError = ''" />
    <div class="metric-grid">
      <article v-for="metric in metrics" :key="metric.label" class="metric-card" :style="{ '--metric-color': metric.color }">
        <div class="label">{{ metric.label }}</div><div class="value">{{ metric.value }}</div><div class="hint">{{ metric.hint }}</div>
      </article>
    </div>

    <div class="dashboard-grid">
      <section class="surface">
        <div class="surface-header"><div><h2>{{ t('dashboard.recentVideos') }}</h2><p>{{ t('dashboard.recentVideosHint') }}</p></div><el-button text type="primary" @click="$router.push('/videos')">{{ t('dashboard.allVideos') }}</el-button></div>
        <DataState :loading="loading" :empty="!videos.length" :empty-text="t('dashboard.noVideos')" @retry="load">
          <el-button type="primary" @click="$router.push('/video/create')">{{ t('dashboard.createVideo') }}</el-button>
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
        <div class="surface-header"><div><h2>{{ t('dashboard.recentPublishes') }}</h2><p>{{ t('dashboard.recentPublishesHint') }}</p></div><el-button text type="primary" @click="$router.push('/publish/history')">{{ t('dashboard.allRecords') }}</el-button></div>
        <DataState :loading="loading" :empty="!tasks.length" :empty-text="t('dashboard.noPublishes')" @retry="load">
          <template #content><div class="strip-list">
            <div v-for="task in tasks" :key="task.id" class="strip-item publish-strip">
              <div class="platform-glyph">{{ task.platform_name.slice(0, 1).toUpperCase() }}</div>
              <div><div class="item-title">{{ task.video_title || t('common.untitledVideo') }}</div><div class="item-meta">{{ task.platform_name }} · {{ task.account_name || t('common.defaultAccount') }}</div></div>
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
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()
const loading = ref(true)
const loadError = ref('')
const videos = ref<VideoAsset[]>([])
const generationTasks = ref<GenerationTask[]>([])
const tasks = ref<PublishTask[]>([])
const userTotal = ref<number | null>(null)
const videoTotal = ref<number | null>(null)
const taskTotal = ref<number | null>(null)
const greeting = computed(() => { const hour = new Date().getHours(); return t(hour < 11 ? 'dashboard.greetingMorning' : hour < 18 ? 'dashboard.greetingAfternoon' : 'dashboard.greetingEvening') })
const today = new Date().toDateString()
const metrics = computed(() => {
  const base = [
    { label: t(auth.isAdmin ? 'dashboard.metrics.allVideos' : 'dashboard.metrics.myVideos'), value: videoTotal.value ?? '—', hint: t(auth.isAdmin ? 'dashboard.metrics.systemAssets' : 'dashboard.metrics.accountAssets'), color: '#2864dc' },
    { label: t('dashboard.metrics.todayTasks'), value: generationTasks.value.filter((item) => new Date(item.created_at).toDateString() === today).length, hint: t('dashboard.metrics.submittedToday'), color: '#169a98' },
    { label: t('dashboard.metrics.generating'), value: generationTasks.value.filter((item) => ['pending', 'processing'].includes(item.status)).length, hint: t('dashboard.metrics.generatingHint'), color: '#c47d16' },
    { label: t('dashboard.metrics.publishSuccess'), value: tasks.value.filter((item) => item.status === 'success').length, hint: t('dashboard.metrics.recentRecords'), color: '#169a77' },
    { label: t('dashboard.metrics.publishFailed'), value: tasks.value.filter((item) => item.status === 'failed').length, hint: t('dashboard.metrics.needsAttention'), color: '#cf4c52' },
  ]
  if (auth.isAdmin) {
    base.push({ label: t('dashboard.metrics.users'), value: userTotal.value ?? '—', hint: t('dashboard.metrics.usersHint'), color: '#6d5bd0' })
    base.push({ label: t('dashboard.metrics.tasks'), value: taskTotal.value ?? '—', hint: t('dashboard.metrics.tasksHint'), color: '#56708f' })
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
  if (results.some((result) => result.status === 'rejected')) loadError.value = t('dashboard.partialLoadFailed')
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
