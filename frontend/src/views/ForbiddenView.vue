<template>
  <div class="state-page"><div class="state-card"><div class="state-code">403</div><h1>{{ $t('statePage.forbiddenTitle') }}</h1><p>{{ $t('statePage.forbiddenText') }}</p><el-button type="primary" @click="$router.replace('/dashboard')">{{ $t('statePage.backDashboard') }}</el-button></div></div>
</template>
