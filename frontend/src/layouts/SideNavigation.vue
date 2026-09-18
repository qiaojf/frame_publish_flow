<template>
  <el-menu :default-active="route.path" router class="side-menu" @select="$emit('navigate')">
    <el-menu-item index="/dashboard"><el-icon><DataLine /></el-icon><span>{{ t('routes.dashboard') }}</span></el-menu-item>
    <div class="menu-label">{{ t('nav.creationAssets') }}</div>
    <el-menu-item index="/video/create"><el-icon><VideoPlay /></el-icon><span>{{ t('routes.createVideo') }}</span></el-menu-item>
    <el-menu-item index="/videos"><el-icon><Film /></el-icon><span>{{ t('routes.videos') }}</span></el-menu-item>
    <div class="menu-label">{{ t('nav.publishManagement') }}</div>
    <el-menu-item index="/publish"><el-icon><Promotion /></el-icon><span>{{ t('routes.publish') }}</span></el-menu-item>
    <el-menu-item index="/publish/history"><el-icon><Clock /></el-icon><span>{{ t('routes.publishHistory') }}</span></el-menu-item>
    <template v-if="auth.isAdmin">
      <div class="menu-label">{{ t('nav.systemManagement') }}</div>
      <el-sub-menu index="/admin">
        <template #title><el-icon><Setting /></el-icon><span>{{ t('nav.systemConfig') }}</span></template>
        <el-menu-item index="/admin/users">{{ t('routes.users') }}</el-menu-item>
        <el-menu-item index="/admin/models">{{ t('routes.models') }}</el-menu-item>
        <el-menu-item index="/admin/platforms">{{ t('routes.platforms') }}</el-menu-item>
        <el-menu-item index="/admin/accounts">{{ t('routes.accounts') }}</el-menu-item>
        <el-menu-item index="/admin/logs">{{ t('routes.logs') }}</el-menu-item>
      </el-sub-menu>
    </template>
  </el-menu>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { Clock, DataLine, Film, Promotion, Setting, VideoPlay } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'

defineEmits<{ navigate: [] }>()
const route = useRoute()
const auth = useAuthStore()
const { t } = useI18n()
</script>
