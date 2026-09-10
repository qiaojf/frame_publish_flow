<template>
  <el-menu :default-active="route.path" router class="side-menu" @select="$emit('navigate')">
    <el-menu-item index="/dashboard"><el-icon><DataLine /></el-icon><span>工作概览</span></el-menu-item>
    <div class="menu-label">制作与资产</div>
    <el-menu-item index="/video/create"><el-icon><VideoPlay /></el-icon><span>制作视频</span></el-menu-item>
    <el-menu-item index="/videos"><el-icon><Film /></el-icon><span>我的视频</span></el-menu-item>
    <div class="menu-label">发布管理</div>
    <el-menu-item index="/publish"><el-icon><Promotion /></el-icon><span>发布视频</span></el-menu-item>
    <el-menu-item index="/publish/history"><el-icon><Clock /></el-icon><span>发布记录</span></el-menu-item>
    <template v-if="auth.isAdmin">
      <div class="menu-label">系统管理</div>
      <el-sub-menu index="/admin">
        <template #title><el-icon><Setting /></el-icon><span>系统配置</span></template>
        <el-menu-item index="/admin/users">用户管理</el-menu-item>
        <el-menu-item index="/admin/models">视频模型</el-menu-item>
        <el-menu-item index="/admin/platforms">发布平台</el-menu-item>
        <el-menu-item index="/admin/accounts">发布账号</el-menu-item>
        <el-menu-item index="/admin/logs">操作日志</el-menu-item>
      </el-sub-menu>
    </template>
  </el-menu>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { Clock, DataLine, Film, Promotion, Setting, VideoPlay } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

defineEmits<{ navigate: [] }>()
const route = useRoute()
const auth = useAuthStore()
</script>
