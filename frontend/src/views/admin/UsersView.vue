<template>
  <div>
    <PageHeader :eyebrow="t('admin.eyebrow')" :title="t('admin.usersTitle')" :description="t('admin.usersIntro')"><template #actions><el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>{{ t('admin.addUser') }}</el-button></template></PageHeader>
    <section class="surface">
      <div class="toolbar"><div class="toolbar-group"><el-input v-model="keyword" clearable :placeholder="t('admin.searchUser')" :prefix-icon="Search" style="width: 240px" @keyup.enter="applySearch" @clear="applySearch" /><el-button @click="applySearch">{{ t('common.search') }}</el-button></div><span class="muted">{{ t('admin.totalUsers', { count: total }) }}</span></div>
      <DataState :loading="loading" :error="error" :empty="!users.length" :empty-text="t('admin.noUsers')" @retry="load">
        <template #content><el-table :data="users"><el-table-column :label="t('common.user')" min-width="200"><template #default="scope"><div class="user-cell"><span class="avatar">{{ (scope.row.display_name || scope.row.username).slice(0, 1).toUpperCase() }}</span><div><div class="item-title">{{ scope.row.display_name || scope.row.username }}</div><div class="item-meta">@{{ scope.row.username }}</div></div></div></template></el-table-column><el-table-column prop="email" :label="t('admin.email')" min-width="190"><template #default="scope">{{ scope.row.email || '—' }}</template></el-table-column><el-table-column :label="t('admin.role')" width="130"><template #default="scope"><el-tag :type="scope.row.role === 'admin' ? 'primary' : 'info'">{{ t(`role.${scope.row.role}`) }}</el-tag></template></el-table-column><el-table-column :label="t('common.status')" width="110"><template #default="scope"><el-switch v-model="scope.row.enabled" :loading="switchingId === scope.row.id" @change="toggleEnabled(scope.row)" /></template></el-table-column><el-table-column :label="t('admin.lastLogin')" min-width="160"><template #default="scope">{{ formatDate(scope.row.last_login_at) }}</template></el-table-column><el-table-column :label="t('common.actions')" width="250" fixed="right"><template #default="scope"><el-button text type="primary" @click="openEdit(scope.row)">{{ t('common.edit') }}</el-button><el-button text @click="resetPassword(scope.row)">{{ t('admin.resetPassword') }}</el-button><el-button text type="danger" @click="remove(scope.row)">{{ t('common.delete') }}</el-button></template></el-table-column></el-table></template>
      </DataState>
      <div v-if="total > pageSize" class="pagination-row"><el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="load" /></div>
    </section>

    <el-dialog v-model="dialogOpen" :title="editingId ? t('admin.editUser') : t('admin.addUser')" width="560px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top"><div class="form-grid"><el-form-item :label="t('auth.username')" prop="username"><el-input v-model="form.username" :disabled="Boolean(editingId)" /></el-form-item><el-form-item :label="t('admin.displayName')"><el-input v-model="form.display_name" /></el-form-item><el-form-item :label="t('admin.email')"><el-input v-model="form.email" /></el-form-item><el-form-item :label="t('admin.role')" prop="role"><el-select v-model="form.role" style="width: 100%"><el-option :label="t('role.user')" value="user" /><el-option :label="t('role.admin')" value="admin" /></el-select></el-form-item><el-form-item v-if="!editingId" :label="t('admin.initialPassword')" prop="password" class="span-2"><el-input v-model="form.password" type="password" show-password autocomplete="new-password" /></el-form-item><el-form-item :label="t('admin.accountStatus')"><el-switch v-model="form.enabled" :active-text="t('common.enabled')" :inactive-text="t('common.disabled')" /></el-form-item></div></el-form>
      <template #footer><el-button @click="dialogOpen = false">{{ t('common.cancel') }}</el-button><el-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'; import DataState from '@/components/DataState.vue'
import { createUser, deleteUser, getUsers, resetUserPassword, updateUser } from '@/api/users'
import type { User, UserInput } from '@/types/user'
import { formatDate } from '@/utils/format'; import { getErrorMessage } from '@/utils/errors'

const users = ref<User[]>([]); const loading = ref(true); const saving = ref(false); const error = ref(''); const keyword = ref(''); const page = ref(1); const pageSize = 20; const total = ref(0); const switchingId = ref('')
const { t } = useI18n()
const dialogOpen = ref(false); const editingId = ref(''); const formRef = ref<FormInstance>()
const form = reactive<UserInput>({ username: '', display_name: '', email: '', role: 'user', enabled: true, password: '' })
const rules = computed<FormRules<UserInput>>(() => ({ username: [{ required: true, message: t('admin.usernameRequired'), trigger: 'blur' }], role: [{ required: true, message: t('admin.roleRequired'), trigger: 'change' }], password: [{ min: 8, message: t('admin.passwordMin'), trigger: 'blur' }] }))
async function load() { loading.value = true; error.value = ''; try { const result = await getUsers({ page: page.value, page_size: pageSize, keyword: keyword.value || undefined }); users.value = result.items; total.value = result.total } catch (reason) { error.value = getErrorMessage(reason, t('admin.userListFailed')) } finally { loading.value = false } }
function applySearch() { page.value = 1; load() }
function resetForm() { Object.assign(form, { username: '', display_name: '', email: '', role: 'user', enabled: true, password: '' }) }
function openCreate() { editingId.value = ''; resetForm(); dialogOpen.value = true }
function openEdit(user: User) { editingId.value = user.id; Object.assign(form, { username: user.username, display_name: user.display_name ?? '', email: user.email ?? '', role: user.role, enabled: user.enabled, password: '' }); dialogOpen.value = true }
async function save() { if (!(await formRef.value?.validate().catch(() => false))) return; saving.value = true; try { if (editingId.value) { await updateUser(editingId.value, { username: form.username, display_name: form.display_name, email: form.email, role: form.role, enabled: form.enabled }) } else await createUser(form); ElMessage.success(t('admin.userSaved')); dialogOpen.value = false; await load() } catch (reason) { ElMessage.error(getErrorMessage(reason, t('admin.userSaveFailed'))) } finally { saving.value = false } }
async function toggleEnabled(user: User) { switchingId.value = user.id; try { await updateUser(user.id, { enabled: user.enabled }); ElMessage.success(t(user.enabled ? 'admin.userEnabled' : 'admin.userDisabled')) } catch (reason) { user.enabled = !user.enabled; ElMessage.error(getErrorMessage(reason, t('admin.statusUpdateFailed'))) } finally { switchingId.value = '' } }
async function resetPassword(user: User) { try { const result = await ElMessageBox.prompt(t('admin.resetPasswordPrompt', { username: user.username }), t('admin.resetPassword'), { inputType: 'password', inputPattern: /^.{8,}$/, inputErrorMessage: t('admin.passwordMin'), confirmButtonText: t('admin.resetPasswordConfirm'), cancelButtonText: t('common.cancel') }); await resetUserPassword(user.id, result.value); ElMessage.success(t('admin.passwordReset')) } catch (reason) { if (reason !== 'cancel' && reason !== 'close') ElMessage.error(getErrorMessage(reason, t('admin.passwordResetFailed'))) } }
async function remove(user: User) { try { await ElMessageBox.confirm(t('admin.deleteUserPrompt', { username: user.username }), t('admin.deleteUserTitle'), { type: 'warning', confirmButtonText: t('common.confirmDelete'), cancelButtonText: t('common.cancel') }); await deleteUser(user.id); ElMessage.success(t('admin.userDeleted')); await load() } catch (reason) { if (reason !== 'cancel' && reason !== 'close') ElMessage.error(getErrorMessage(reason, t('video.deleteFailed'))) } }
onMounted(load)
</script>

<style scoped>.user-cell { display: flex; gap: 10px; align-items: center; }</style>
