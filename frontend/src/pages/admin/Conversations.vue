<script setup lang="ts">
import { ref } from 'vue'
import DataTable from '@/components/admin/DataTable.vue'

const conversations = ref([
  { id: 'conv_001', user: 'zhangsan', title: '查询北京到上海航班', messages: 12, tokens: 2345, created: '2026-05-01 14:30', status: 'completed' },
  { id: 'conv_002', user: 'lisi', title: '预订三亚酒店', messages: 8, tokens: 1567, created: '2026-05-01 15:45', status: 'completed' },
  { id: 'conv_003', user: 'wangwu', title: '租车咨询', messages: 5, tokens: 890, created: '2026-05-02 09:12', status: 'active' },
])

const columns = [
  { key: 'id', label: 'ID', sortable: true, width: '120px' },
  { key: 'user', label: '用户', sortable: true },
  { key: 'title', label: '主题', sortable: true },
  { key: 'messages', label: '消息数', sortable: true, width: '80px' },
  { key: 'tokens', label: 'Token', sortable: true, width: '80px' },
  { key: 'created', label: '创建时间', sortable: true },
  { key: 'status', label: '状态', sortable: true, width: '100px' },
]
</script>

<template>
  <div class="p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">对话记录</h1>
        <p class="text-sm text-gray-500 mt-1">监控用户对话内容</p>
      </div>
    </div>

    <DataTable
      :columns="columns"
      :data="conversations as unknown as Record<string, unknown>[]"
      searchable
      :searchKeys="['id', 'user', 'title']"
    >
      <template #cell-status="{ row }">
        <span
          class="inline-flex px-2 py-0.5 text-xs font-medium rounded-full"
          :class="row.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'"
        >
          {{ row.status === 'active' ? '进行中' : '已完成' }}
        </span>
      </template>
      <template #cell-actions="{ row }">
        <button class="text-xs text-primary-600 hover:text-primary-800 font-medium">查看</button>
      </template>
    </DataTable>
  </div>
</template>
