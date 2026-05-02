<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useRouter } from 'vue-router'

const chatStore = useChatStore()
const router = useRouter()

const showDropdown = ref(false)

function newChat() {
  chatStore.newSession()
  showDropdown.value = false
}

function selectSession(id: string) {
  chatStore.selectSession(id)
  showDropdown.value = false
}

function toggleDropdown() {
  if (chatStore.sessions.length > 0) {
    showDropdown.value = !showDropdown.value
  }
}
</script>

<template>
  <header class="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-white">
    <div class="flex items-center gap-2">
      <button
        class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors lg:hidden"
        @click="chatStore.toggleSidebar()"
        title="切换侧栏"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M3 12h18M3 6h18M3 18h18" />
        </svg>
      </button>
      <div class="relative">
        <button
          class="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
          @click="toggleDropdown"
        >
          <h1 class="text-sm font-semibold text-gray-800 truncate max-w-[200px]">
            {{ chatStore.currentSession?.title || '新对话' }}
          </h1>
          <svg v-if="chatStore.sessions.length > 0" class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
        <div
          v-if="showDropdown"
          class="absolute top-full left-0 mt-1 w-64 bg-white rounded-xl shadow-lg border border-gray-100 py-1 z-50 max-h-64 overflow-y-auto"
        >
          <button
            v-for="s in chatStore.sessions"
            :key="s.id"
            class="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 transition-colors truncate"
            :class="{ 'bg-primary-50 text-primary-700': s.id === chatStore.currentSessionId }"
            @click="selectSession(s.id)"
          >
            {{ s.title || '新对话' }}
          </button>
        </div>
      </div>
    </div>
    <div class="flex items-center gap-1">
      <button
        class="p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
        @click="newChat"
        title="新建对话"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
    </div>
  </header>
</template>
