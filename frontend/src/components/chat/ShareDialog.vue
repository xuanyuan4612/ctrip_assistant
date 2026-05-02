<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  visible: boolean
}>()

const pageUrl = window.location.href

const emit = defineEmits<{
  close: []
}>()

const copied = ref(false)

function copyLink() {
  navigator.clipboard.writeText(window.location.href)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="emit('close')"></div>

      <!-- Dialog -->
      <div class="relative bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md mx-4">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">分享对话</h3>
          <button class="p-1 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors" @click="emit('close')">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <p class="text-sm text-gray-500 mb-4">通过链接分享当前对话内容</p>

        <div class="flex items-center gap-2 p-2 bg-gray-50 rounded-lg border border-gray-200">
          <input
            type="text"
            :value="pageUrl"
            readonly
            class="flex-1 bg-transparent text-sm text-gray-600 outline-none px-2"
          />
          <button
            class="px-4 py-1.5 text-sm font-medium rounded-lg transition-colors"
            :class="copied ? 'bg-green-500 text-white' : 'bg-primary-600 text-white hover:bg-primary-700'"
            @click="copyLink"
          >
            {{ copied ? '已复制' : '复制' }}
          </button>
        </div>

        <div class="mt-6 pt-4 border-t border-gray-100">
          <p class="text-xs text-gray-400">分享链接将包含当前对话的所有消息记录</p>
        </div>
      </div>
    </div>
  </Teleport>
</template>
