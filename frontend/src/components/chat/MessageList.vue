<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import MessageBubble from './MessageBubble.vue'
import LoadingDots from '@/components/shared/LoadingDots.vue'

const chatStore = useChatStore()
const listRef = ref<HTMLElement | null>(null)

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}

watch(() => chatStore.messages.length, () => scrollToBottom())
watch(() => chatStore.messages.map(m => m.content).join(''), () => scrollToBottom())
</script>

<template>
  <div
    ref="listRef"
    class="flex-1 overflow-y-auto bg-gray-50/50"
  >
    <!-- Empty state -->
    <div v-if="chatStore.messages.length === 0" class="flex flex-col items-center justify-center h-full text-center px-6">
      <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-indigo-600 flex items-center justify-center mb-4 shadow-lg">
        <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M12 2a4 4 0 014 4v2a4 4 0 01-8 0V6a4 4 0 014-4z" />
          <path d="M16 14H8a4 4 0 00-4 4v2a2 2 0 002 2h12a2 2 0 002-2v-2a4 4 0 00-4-4z" />
        </svg>
      </div>
      <h2 class="text-xl font-semibold text-gray-700 mb-2">携程 AI 助手</h2>
      <p class="text-sm text-gray-400 max-w-sm">您好！我是携程 AI 助手，可以帮您查询航班、酒店、租车等信息，请提出您的需求。</p>
    </div>

    <!-- Messages -->
    <div v-else class="py-4">
      <MessageBubble v-for="msg in chatStore.messages" :key="msg.id" :message="msg" />
      <LoadingDots v-if="chatStore.isStreaming" />
    </div>
  </div>
</template>
