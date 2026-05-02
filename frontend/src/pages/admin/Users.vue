<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchUsers } from '@/api/client'
import type { User } from '@/types'
import DataTable from '@/components/admin/DataTable.vue'

const users = ref<User[]>([])
const loading = ref(true)

const columns = [
  { key: 'id', label: 'ID', sortable: true, width: '80px' },
  { key: 'username', label: '用户名', sortable: true },
  { key: 'phone', label: '手机号', sortable: true },
  { key: 'realName', label: '真实姓名', sortable: true },
  { key: 'actions', label: '操作', width: '120px' },
]

onMounted(async () => {
  try {
    const data = await fetchUsers()
    users.value = data as User[]
  } catch {
    // Placeholder fallback
    users.value = [
      { id: 1, username: 'admin', phone: '138****8888', realName: '管理员' },
      { id: 2, username: 'zhangsan', phone: '139****1234', realName: '张三' },
      { id: 3, username: 'lisi', phone: '137****5678', realName: '李四' },
    ]
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">用户管理</h1>
        <p class="text-sm text-gray-500 mt-1">查看和管理系统用户</p>
      </div>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-20">
      <svg class="w-8 h-8 animate-spin text-primary-600" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <DataTable
      v-else
      :columns="columns"
      :data="users as unknown as Record<string, unknown>[]"
      searchable
      :searchKeys="['username', 'phone', 'realName']"
    >
      <template #cell-actions="{ row }">
        <div class="flex items-center gap-2">
          <button class="text-xs text-primary-600 hover:text-primary-800 font-medium">编辑</button>
          <button class="text-xs text-red-500 hover:text-red-700 font-medium">禁用</button>
        </div>
      </template>
    </DataTable>
  </div>
</template>
