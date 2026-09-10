<template>
  <div class="state-page"><div class="state-card"><div class="state-code">403</div><h1>这里需要管理员权限</h1><p>当前账号不能访问系统配置。后端仍会对所有管理操作进行独立权限校验。</p><el-button type="primary" @click="$router.replace('/dashboard')">返回工作概览</el-button></div></div>
</template>
