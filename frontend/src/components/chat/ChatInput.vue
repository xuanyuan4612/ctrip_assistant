<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const input = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const emit = defineEmits<{
  send: [text: string]
}>()

function autoResize() {
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
      textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 160) + 'px'
    }
  })
}

function handleSend() {
  const text = input.value.trim()
  if (!text || chatStore.isStreaming) return
  input.value = ''
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
  emit('send', text)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="border-t border-gray-100 bg-white px-4 py-3">
    <div class="max-w-4xl mx-auto flex items-end gap-2 bg-gray-50 rounded-2xl border border-gray-200 px-4 py-2 focus-within:ring-2 focus-within:ring-primary-500 focus-within:border-primary-500 transition-all">
      <button class="p-1.5 text-gray-400 hover:text-gray-600 transition-colors shrink-0" title="上传文件">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
        </svg>
      </button>
      <textarea
        ref="textareaRef"
        v-model="input"
        rows="1"
        placeholder="输入消息..."
        class="flex-1 bg-transparent resize-none outline-none text-sm text-gray-700 py-1.5 placeholder-gray-400 max-h-40"
        :disabled="chatStore.isStreaming"
        @input="autoResize"
        @keydown="onKeydown"
      ></textarea>
      <button
        class="p-2 rounded-xl bg-primary-600 text-white hover:bg-primary-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
        :disabled="!input.trim() || chatStore.isStreaming"
        @click="handleSend"
        title="发送"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
        </svg>
      </button>
    </div>
  </div>
</template>
