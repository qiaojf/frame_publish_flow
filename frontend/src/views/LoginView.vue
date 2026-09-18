<template>
  <div class="login-page">
    <LanguageSwitcher class="login-language-switcher" />
    <section class="login-panel">
      <div class="login-brand"><BrandMark /><strong>FrameFlow</strong></div>
      <div class="login-copy">
        <div class="kicker">{{ t('auth.kicker') }}</div>
        <h1>{{ t('auth.headlineLine1') }}<br />{{ t('auth.headlineLine2') }}</h1>
        <p>{{ t('auth.intro') }}</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" class="login-form" label-position="top" @submit.prevent="submit">
        <el-form-item :label="t('auth.username')" prop="username">
          <el-input v-model="form.username" size="large" autocomplete="username" :placeholder="t('auth.usernamePlaceholder')" :prefix-icon="User" />
        </el-form-item>
        <el-form-item :label="t('auth.password')" prop="password">
          <el-input v-model="form.password" size="large" type="password" autocomplete="current-password" :placeholder="t('auth.passwordPlaceholder')" show-password :prefix-icon="Lock" @keyup.enter="submit" />
        </el-form-item>
        <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
        <el-button type="primary" native-type="submit" :loading="loading">{{ t('auth.submit') }}</el-button>
      </el-form>
      <p class="login-footnote">{{ t('auth.footnote') }}</p>
    </section>
    <section class="login-visual" :aria-label="t('auth.visualAria')">
      <div class="visual-content">
        <p>{{ t('auth.visualIntro') }}</p>
        <div class="storyboard">
          <div class="story-frame">
            <div class="story-label">{{ t('auth.production') }}</div>
            <h2>{{ t('auth.workflowPrompt') }}<br />→ {{ t('auth.workflowVideo') }}<br />→ {{ t('auth.workflowPublish') }}</h2>
            <span class="story-status">● {{ t('auth.tracked') }}</span>
          </div>
          <div class="story-frame"><div class="story-label">{{ t('auth.assets') }}</div><div class="big-number">01</div><span class="story-status">{{ t('auth.managed') }}</span></div>
          <div class="story-frame"><div class="story-label">{{ t('auth.channels') }}</div><div class="big-number">∞</div><span class="story-status">{{ t('auth.dynamic') }}</span></div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { Lock, User } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import BrandMark from '@/components/BrandMark.vue'
import { useAuthStore } from '@/stores/auth'
import { getErrorMessage } from '@/utils/errors'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { t } = useI18n()
const formRef = ref<FormInstance>()
const loading = ref(false)
const error = ref('')
const form = reactive({ username: '', password: '' })
const rules = computed<FormRules<typeof form>>(() => ({
  username: [{ required: true, message: t('auth.usernamePlaceholder'), trigger: 'blur' }],
  password: [{ required: true, message: t('auth.passwordPlaceholder'), trigger: 'blur' }],
}))

async function submit() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  loading.value = true
  error.value = ''
  try {
    await auth.login(form)
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') ? route.query.redirect : '/dashboard'
    await router.replace(redirect)
  } catch (reason) {
    error.value = getErrorMessage(reason, t('auth.loginFailed'))
  } finally { loading.value = false }
}
</script>

<style scoped>
.login-language-switcher { position: absolute; z-index: 2; top: 22px; right: 24px; }
</style>
