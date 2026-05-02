<script setup lang="ts">
import { ref } from 'vue'

const documents = ref([
  { id: 1, name: '携程酒店API文档.pdf', type: 'PDF', size: '2.3 MB', uploaded: '2026-04-28', chunks: 45, status: 'completed' },
  { id: 2, name: '航班查询接口说明.docx', type: 'DOCX', size: '1.1 MB', uploaded: '2026-04-29', chunks: 28, status: 'completed' },
  { id: 3, name: '租车服务FAQ.txt', type: 'TXT', size: '156 KB', uploaded: '2026-04-30', chunks: 12, status: 'processing' },
])

const dragOver = ref(false)

function handleFileUpload() {
  // Placeholder: implement file upload logic
}
</script>

<template>
  <div class="p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">文档管理</h1>
        <p class="text-sm text-gray-500 mt-1">上传和管理 RAG 知识库文档</p>
      </div>
      <button class="btn-primary text-sm" @click="handleFileUpload">
        上传文档
      </button>
    </div>

    <!-- Upload area -->
    <div
      :class="[
        'border-2 border-dashed rounded-xl p-10 text-center transition-colors mb-6',
        dragOver ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300 bg-white'
      ]"
      @dragover.prevent="dragOver = true"
      @dragleave.prevent="dragOver = false"
      @drop.prevent="dragOver = false; handleFileUpload()"
    >
      <svg class="w-10 h-10 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
      <p class="text-sm text-gray-500">拖拽文件到此处上传，或点击上方按钮选择文件</p>
      <p class="text-xs text-gray-400 mt-1">支持 PDF、DOCX、TXT 格式</p>
    </div>

    <!-- Document list -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-gray-50 border-b border-gray-100">
            <th class="px-4 py-3 text-left font-medium text-gray-500">文件名</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">类型</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">大小</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">上传时间</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">分块数</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">状态</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-for="doc in documents" :key="doc.id" class="hover:bg-gray-50 transition-colors">
            <td class="px-4 py-3 text-gray-700 font-medium">{{ doc.name }}</td>
            <td class="px-4 py-3">
              <span class="text-xs font-medium px-2 py-0.5 rounded bg-gray-100 text-gray-600">{{ doc.type }}</span>
            </td>
            <td class="px-4 py-3 text-gray-600">{{ doc.size }}</td>
            <td class="px-4 py-3 text-gray-600">{{ doc.uploaded }}</td>
            <td class="px-4 py-3 text-gray-600">{{ doc.chunks }}</td>
            <td class="px-4 py-3">
              <span
                class="inline-flex px-2 py-0.5 text-xs font-medium rounded-full"
                :class="doc.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'"
              >
                {{ doc.status === 'completed' ? '已完成' : '处理中' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <button class="text-xs text-primary-600 hover:text-primary-800 font-medium">查看</button>
                <button class="text-xs text-red-500 hover:text-red-700 font-medium">删除</button>
              </div>
            </td>
          </tr>
          <tr v-if="documents.length === 0">
            <td colspan="7" class="px-4 py-8 text-center text-gray-400">暂无文档</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
