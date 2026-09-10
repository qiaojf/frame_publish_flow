<template>
  <div class="login-page">
    <section class="login-panel">
      <div class="login-brand"><BrandMark /><strong>FrameFlow</strong></div>
      <div class="login-copy">
        <div class="kicker">Enterprise video operations</div>
        <h1>把灵感推进到<br />每一个发布终点。</h1>
        <p>统一完成 AI 视频制作、资产管理与多平台发布。登录后，系统会依据账号角色开放对应工作区。</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" class="login-form" label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" size="large" autocomplete="username" placeholder="请输入用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" size="large" type="password" autocomplete="current-password" placeholder="请输入密码" show-password :prefix-icon="Lock" @keyup.enter="submit" />
        </el-form-item>
        <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
        <el-button type="primary" native-type="submit" :loading="loading">登录工作台</el-button>
      </el-form>
      <p class="login-footnote">账号与权限由管理员配置。前端仅改善访问体验，最终权限始终由服务端校验。</p>
    </section>
    <section class="login-visual" aria-label="平台能力概览">
      <div class="visual-content">
        <p>从生成任务到平台回执，每个动作都在同一条可追踪的生产轨道中。</p>
        <div class="storyboard">
          <div class="story-frame">
            <div class="story-label">PRODUCTION / 生成</div>
            <h2>Prompt<br />→ Video<br />→ Publish</h2>
            <span class="story-status">● 任务独立追踪</span>
          </div>
          <div class="story-frame"><div class="story-label">ASSETS / 视频资产</div><div class="big-number">01</div><span class="story-status">统一管理</span></div>
          <div class="story-frame"><div class="story-label">CHANNELS / 发布平台</div><div class="big-number">∞</div><span class="story-status">能力动态加载</span></div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Lock, User } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import BrandMark from '@/components/BrandMark.vue'
import { useAuthStore } from '@/stores/auth'
import { getErrorMessage } from '@/utils/errors'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const error = ref('')
const form = reactive({ username: '', password: '' })
const rules: FormRules<typeof form> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  loading.value = true
  error.value = ''
  try {
    await auth.login(form)
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') ? route.query.redirect : '/dashboard'
    await router.replace(redirect)
  } catch (reason) {
    error.value = getErrorMessage(reason, '登录失败，请检查用户名和密码')
  } finally { loading.value = false }
}
</script>
