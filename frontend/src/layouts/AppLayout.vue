<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="sidebar-brand"><BrandMark /><div><strong>FrameFlow</strong><span>视频生产工作台</span></div></div>
      <SideNavigation />
      <div class="sidebar-foot"><span class="live-dot" /><div><strong>API 驱动模式</strong><small>所有操作由后端校验</small></div></div>
    </aside>
    <el-drawer v-model="drawerOpen" direction="ltr" size="280px" :with-header="false" class="mobile-drawer">
      <div class="sidebar-brand drawer-brand"><BrandMark /><div><strong>FrameFlow</strong><span>视频生产工作台</span></div></div>
      <SideNavigation @navigate="drawerOpen = false" />
    </el-drawer>
    <div class="workspace">
      <header class="topbar">
        <button class="menu-trigger" type="button" aria-label="打开导航" @click="drawerOpen = true"><Menu :size="20" /></button>
        <div class="breadcrumb">{{ route.meta.title ?? '工作台' }}</div>
        <div class="topbar-right">
          <el-tooltip content="刷新当前页面"><button class="icon-button" type="button" @click="reload"><Refresh :size="17" /></button></el-tooltip>
          <div class="user-divider" />
          <el-dropdown trigger="click" @command="handleCommand">
            <button class="user-menu" type="button">
              <span class="avatar">{{ initials }}</span>
              <span class="user-copy"><strong>{{ auth.user?.display_name || auth.user?.username }}</strong><small>{{ auth.isAdmin ? '管理员' : '普通用户' }}</small></span>
              <ArrowDown :size="14" />
            </button>
            <template #dropdown><el-dropdown-menu><el-dropdown-item command="logout">退出登录</el-dropdown-item></el-dropdown-menu></template>
          </el-dropdown>
        </div>
      </header>
      <main class="page-frame"><RouterView :key="route.fullPath" /></main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter, RouterView } from 'vue-router'
import { ArrowDown, Menu, Refresh } from '@element-plus/icons-vue'
import BrandMark from '@/components/BrandMark.vue'
import SideNavigation from './SideNavigation.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const drawerOpen = ref(false)
const initials = computed(() => (auth.user?.display_name || auth.user?.username || 'U').slice(0, 1).toUpperCase())
function reload() { router.go(0) }
function handleCommand(command: string) {
  if (command === 'logout') { auth.logout(); router.replace('/login') }
}
</script>
