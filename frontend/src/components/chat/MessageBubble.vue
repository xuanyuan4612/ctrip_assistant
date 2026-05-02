<script setup lang="ts">
import { computed } from 'vue'
import type { Message } from '@/types'
import BookingCard from './BookingCard.vue'

const props = defineProps<{
  message: Message
}>()

const isUser = computed(() => props.message.role === 'user')

function renderMarkdown(content: string): string {
  // Simple markdown rendering with DOMPurify-like approach (basic)
  // In production, use marked + DOMPurify
  let html = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-50 rounded-lg p-3 text-xs overflow-x-auto my-2 border border-gray-200"><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1.5 py-0.5 rounded text-sm text-pink-600">$1</code>')
    .replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-bold mt-3 mb-1">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-bold mt-4 mb-1">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold mt-4 mb-2">$1</h1>')
    .replace(/^[-*] (.+)$/gm, '<li class="ml-4 list-disc text-sm">$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li class="ml-4 list-decimal text-sm">$1. $2</li>')
    .replace(/\n\n/g, '</p><p class="mb-2">')
    .replace(/\n/g, '<br/>')
  return '<p class="mb-2">' + html + '</p>'
}

const renderedContent = computed(() => renderMarkdown(props.message.content))
</script>

<template>
  <div :class="['flex gap-3 px-4 py-3', isUser ? 'justify-end' : 'justify-start']">
    <!-- Assistant avatar -->
    <div v-if="!isUser" class="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-indigo-600 flex items-center justify-center shrink-0 mt-1">
      <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M12 2a4 4 0 014 4v2a4 4 0 01-8 0V6a4 4 0 014-4z" />
        <path d="M16 14H8a4 4 0 00-4 4v2a2 2 0 002 2h12a2 2 0 002-2v-2a4 4 0 00-4-4z" />
      </svg>
    </div>

    <div :class="['max-w-[75%] rounded-2xl px-4 py-2.5', isUser ? 'bg-primary-600 text-white rounded-br-md' : 'bg-white border border-gray-100 shadow-sm rounded-bl-md']">
      <!-- Markdown content for assistant, plain text for user -->
      <div v-if="isUser" class="text-sm whitespace-pre-wrap">{{ message.content }}</div>
      <div v-else class="text-sm text-gray-700 prose prose-sm max-w-none" v-html="renderedContent"></div>

      <!-- Booking cards -->
      <div v-if="message.bookingCards && message.bookingCards.length > 0" class="mt-2 space-y-2">
        <BookingCard v-for="(card, idx) in message.bookingCards" :key="idx" :card="card" />
      </div>

      <!-- Streaming indicator -->
      <div v-if="message.streaming" class="flex gap-1 mt-1">
        <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse"></span>
        <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style="animation-delay: 200ms"></span>
        <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style="animation-delay: 400ms"></span>
      </div>
    </div>

    <!-- User avatar -->
    <div v-if="isUser" class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0 mt-1">
      <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    </div>
  </div>
</template>
