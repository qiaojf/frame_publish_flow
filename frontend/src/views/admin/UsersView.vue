<template>
  <div>
    <PageHeader eyebrow="Administration" title="用户管理" description="管理系统账号、角色与启用状态。角色校验最终由后端执行。"><template #actions><el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新增用户</el-button></template></PageHeader>
    <section class="surface">
      <div class="toolbar"><div class="toolbar-group"><el-input v-model="keyword" clearable placeholder="搜索用户名或邮箱" :prefix-icon="Search" style="width: 240px" @keyup.enter="applySearch" @clear="applySearch" /><el-button @click="applySearch">搜索</el-button></div><span class="muted">共 {{ total }} 个用户</span></div>
      <DataState :loading="loading" :error="error" :empty="!users.length" empty-text="暂无用户" @retry="load">
        <template #content><el-table :data="users"><el-table-column label="用户" min-width="200"><template #default="scope"><div class="user-cell"><span class="avatar">{{ (scope.row.display_name || scope.row.username).slice(0, 1).toUpperCase() }}</span><div><div class="item-title">{{ scope.row.display_name || scope.row.username }}</div><div class="item-meta">@{{ scope.row.username }}</div></div></div></template></el-table-column><el-table-column prop="email" label="邮箱" min-width="190"><template #default="scope">{{ scope.row.email || '—' }}</template></el-table-column><el-table-column label="角色" width="110"><template #default="scope"><el-tag :type="scope.row.role === 'admin' ? 'primary' : 'info'">{{ scope.row.role === 'admin' ? '管理员' : '普通用户' }}</el-tag></template></el-table-column><el-table-column label="状态" width="110"><template #default="scope"><el-switch v-model="scope.row.enabled" :loading="switchingId === scope.row.id" @change="toggleEnabled(scope.row)" /></template></el-table-column><el-table-column label="最近登录" min-width="160"><template #default="scope">{{ formatDate(scope.row.last_login_at) }}</template></el-table-column><el-table-column label="操作" width="230" fixed="right"><template #default="scope"><el-button text type="primary" @click="openEdit(scope.row)">编辑</el-button><el-button text @click="resetPassword(scope.row)">重置密码</el-button><el-button text type="danger" @click="remove(scope.row)">删除</el-button></template></el-table-column></el-table></template>
      </DataState>
      <div v-if="total > pageSize" class="pagination-row"><el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="load" /></div>
    </section>

    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑用户' : '新增用户'" width="560px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top"><div class="form-grid"><el-form-item label="用户名" prop="username"><el-input v-model="form.username" :disabled="Boolean(editingId)" /></el-form-item><el-form-item label="显示名称"><el-input v-model="form.display_name" /></el-form-item><el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item><el-form-item label="角色" prop="role"><el-select v-model="form.role" style="width: 100%"><el-option label="普通用户" value="user" /><el-option label="管理员" value="admin" /></el-select></el-form-item><el-form-item v-if="!editingId" label="初始密码" prop="password" class="span-2"><el-input v-model="form.password" type="password" show-password autocomplete="new-password" /></el-form-item><el-form-item label="账号状态"><el-switch v-model="form.enabled" active-text="启用" inactive-text="停用" /></el-form-item></div></el-form>
      <template #footer><el-button @click="dialogOpen = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Plus, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'; import DataState from '@/components/DataState.vue'
import { createUser, deleteUser, getUsers, resetUserPassword, updateUser } from '@/api/users'
import type { User, UserInput } from '@/types/user'
import { formatDate } from '@/utils/format'; import { getErrorMessage } from '@/utils/errors'

const users = ref<User[]>([]); const loading = ref(true); const saving = ref(false); const error = ref(''); const keyword = ref(''); const page = ref(1); const pageSize = 20; const total = ref(0); const switchingId = ref('')
const dialogOpen = ref(false); const editingId = ref(''); const formRef = ref<FormInstance>()
const form = reactive<UserInput>({ username: '', display_name: '', email: '', role: 'user', enabled: true, password: '' })
const rules: FormRules<UserInput> = { username: [{ required: true, message: '请输入用户名', trigger: 'blur' }], role: [{ required: true, message: '请选择角色', trigger: 'change' }], password: [{ min: 8, message: '密码至少 8 位', trigger: 'blur' }] }
async function load() { loading.value = true; error.value = ''; try { const result = await getUsers({ page: page.value, page_size: pageSize, keyword: keyword.value || undefined }); users.value = result.items; total.value = result.total } catch (reason) { error.value = getErrorMessage(reason, '用户列表加载失败') } finally { loading.value = false } }
function applySearch() { page.value = 1; load() }
function resetForm() { Object.assign(form, { username: '', display_name: '', email: '', role: 'user', enabled: true, password: '' }) }
function openCreate() { editingId.value = ''; resetForm(); dialogOpen.value = true }
function openEdit(user: User) { editingId.value = user.id; Object.assign(form, { username: user.username, display_name: user.display_name ?? '', email: user.email ?? '', role: user.role, enabled: user.enabled, password: '' }); dialogOpen.value = true }
async function save() { if (!(await formRef.value?.validate().catch(() => false))) return; saving.value = true; try { if (editingId.value) { await updateUser(editingId.value, { username: form.username, display_name: form.display_name, email: form.email, role: form.role, enabled: form.enabled }) } else await createUser(form); ElMessage.success('用户已保存'); dialogOpen.value = false; await load() } catch (reason) { ElMessage.error(getErrorMessage(reason, '用户保存失败')) } finally { saving.value = false } }
async function toggleEnabled(user: User) { switchingId.value = user.id; try { await updateUser(user.id, { enabled: user.enabled }); ElMessage.success(user.enabled ? '用户已启用' : '用户已停用') } catch (reason) { user.enabled = !user.enabled; ElMessage.error(getErrorMessage(reason, '状态更新失败')) } finally { switchingId.value = '' } }
async function resetPassword(user: User) { try { const result = await ElMessageBox.prompt(`为 @${user.username} 设置新密码`, '重置密码', { inputType: 'password', inputPattern: /^.{8,}$/, inputErrorMessage: '密码至少 8 位', confirmButtonText: '确认重置' }); await resetUserPassword(user.id, result.value); ElMessage.success('密码已重置') } catch (reason) { if (reason !== 'cancel' && reason !== 'close') ElMessage.error(getErrorMessage(reason, '密码重置失败')) } }
async function remove(user: User) { try { await ElMessageBox.confirm(`确定删除用户 @${user.username}？此操作不可恢复。`, '删除用户', { type: 'warning', confirmButtonText: '确认删除' }); await deleteUser(user.id); ElMessage.success('用户已删除'); await load() } catch (reason) { if (reason !== 'cancel' && reason !== 'close') ElMessage.error(getErrorMessage(reason, '删除失败')) } }
onMounted(load)
</script>

<style scoped>.user-cell { display: flex; gap: 10px; align-items: center; }</style>
