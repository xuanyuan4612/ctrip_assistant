<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  columns: { key: string; label: string; sortable?: boolean; width?: string }[]
  data: Record<string, unknown>[]
  searchable?: boolean
  searchKeys?: string[]
}>()

const emit = defineEmits<{
  sort: [key: string, direction: 'asc' | 'desc']
}>()

const searchQuery = ref('')
const sortKey = ref('')
const sortDir = ref<'asc' | 'desc'>('asc')
const currentPage = ref(1)
const perPage = ref(10)

const filteredData = computed(() => {
  if (!searchQuery.value || !props.searchKeys?.length) return props.data
  const q = searchQuery.value.toLowerCase()
  return props.data.filter(row =>
    props.searchKeys!.some(k => String(row[k] ?? '').toLowerCase().includes(q))
  )
})

const sortedData = computed(() => {
  if (!sortKey.value) return filteredData.value
  return [...filteredData.value].sort((a, b) => {
    const av = a[sortKey.value]
    const bv = b[sortKey.value]
    if (av == null) return 1
    if (bv == null) return -1
    const cmp = String(av).localeCompare(String(bv), 'zh-CN', { numeric: true })
    return sortDir.value === 'asc' ? cmp : -cmp
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(sortedData.value.length / perPage.value)))
const pagedData = computed(() => {
  const start = (currentPage.value - 1) * perPage.value
  return sortedData.value.slice(start, start + perPage.value)
})

function toggleSort(key: string) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
  emit('sort', sortKey.value, sortDir.value)
}
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
    <div v-if="searchable" class="p-4 border-b border-gray-100">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索..."
        class="w-full max-w-xs px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
      />
    </div>
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-gray-50 border-b border-gray-100">
            <th
              v-for="col in columns"
              :key="col.key"
              :style="col.width ? { width: col.width } : {}"
              :class="[
                'px-4 py-3 text-left font-medium text-gray-500',
                col.sortable ? 'cursor-pointer hover:text-gray-700 select-none' : ''
              ]"
              @click="col.sortable && toggleSort(col.key)"
            >
              <span class="inline-flex items-center gap-1">
                {{ col.label }}
                <svg v-if="col.sortable && sortKey === col.key" class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path v-if="sortDir === 'asc'" d="M5 15l7-7 7 7" />
                  <path v-else d="M19 9l-7 7-7-7" />
                </svg>
                <svg v-else-if="col.sortable" class="w-3 h-3 text-gray-300" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path d="M8 7l4-4 4 4M8 17l4 4 4-4" />
                </svg>
              </span>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-for="(row, i) in pagedData" :key="i" class="hover:bg-gray-50 transition-colors">
            <td v-for="col in columns" :key="col.key" class="px-4 py-3 text-gray-700">
              <slot :name="'cell-' + col.key" :row="row" :col="col">
                {{ row[col.key] }}
              </slot>
            </td>
          </tr>
          <tr v-if="pagedData.length === 0">
            <td :colspan="columns.length" class="px-4 py-8 text-center text-gray-400">
              暂无数据
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="totalPages > 1" class="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
      <span class="text-sm text-gray-500">共 {{ sortedData.length }} 条</span>
      <div class="flex items-center gap-1">
        <button
          :disabled="currentPage <= 1"
          class="px-3 py-1 text-sm rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
          @click="currentPage > 1 && currentPage--"
        >上一页</button>
        <span class="px-3 py-1 text-sm text-gray-600">{{ currentPage }} / {{ totalPages }}</span>
        <button
          :disabled="currentPage >= totalPages"
          class="px-3 py-1 text-sm rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
          @click="currentPage < totalPages && currentPage++"
        >下一页</button>
      </div>
    </div>
  </div>
</template>
