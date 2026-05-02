<script setup lang="ts">
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()

function newSession() {
  chatStore.newSession()
}

function formatTime(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - d.getTime()
    if (diff < 60000) return '刚刚'
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
    return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  } catch {
    return ''
  }
}
</script>

<template>
  <aside
    :class="[
      'flex flex-col h-full bg-gray-900 text-gray-300 transition-all duration-300 overflow-hidden',
      chatStore.sidebarOpen ? 'w-64' : 'w-0'
    ]"
  >
    <!-- New chat button -->
    <div class="p-3 border-b border-gray-700/50">
      <button
        class="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium transition-colors"
        @click="newSession"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M12 5v14M5 12h14" />
        </svg>
        新建对话
      </button>
    </div>

    <!-- Session list -->
    <div class="flex-1 overflow-y-auto py-2">
      <div
        v-for="s in chatStore.sessions"
        :key="s.id"
        :class="[
          'group relative flex items-center gap-2 px-3 py-2.5 mx-2 rounded-lg cursor-pointer transition-colors',
          s.id === chatStore.currentSessionId
            ? 'bg-gray-700/60 text-white'
            : 'hover:bg-gray-800/60 text-gray-400 hover:text-gray-200'
        ]"
        @click="chatStore.selectSession(s.id)"
      >
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
        </svg>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium truncate">{{ s.title || '新对话' }}</p>
          <p class="text-xs text-gray-500 truncate mt-0.5">{{ s.lastMessage || '空对话' }}</p>
        </div>
        <span class="text-[10px] text-gray-600 shrink-0">{{ formatTime(s.updatedAt) }}</span>
        <button
          class="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded bg-gray-700 text-gray-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
          title="删除"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
            <path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Bottom branding -->
    <div class="p-3 border-t border-gray-700/50">
      <p class="text-xs text-gray-600 text-center">携程 AI 助手</p>
    </div>
  </aside>
</template>
