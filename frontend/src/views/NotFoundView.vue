<template>
  <div class="state-page"><div class="state-card"><div class="state-code">404</div><h1>{{ $t('statePage.notFoundTitle') }}</h1><p>{{ $t('statePage.notFoundText') }}</p><el-button type="primary" @click="$router.replace('/dashboard')">{{ $t('statePage.backDashboard') }}</el-button></div></div>
</template>
