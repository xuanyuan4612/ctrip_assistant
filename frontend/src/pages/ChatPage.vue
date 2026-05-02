<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import { chatSSE } from '@/api/client'
import type { Message } from '@/types'
import SessionSidebar from '@/components/chat/SessionSidebar.vue'
import ChatHeader from '@/components/chat/ChatHeader.vue'
import MessageList from '@/components/chat/MessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'

const chatStore = useChatStore()
const activeSessionId = ref<string | null>(null)

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

function handleSend(text: string) {
  // Add user message
  const userMsg: Message = {
    id: generateId(),
    role: 'user',
    content: text,
    timestamp: new Date().toISOString(),
  }
  chatStore.addMessage(userMsg)

  // Add placeholder assistant message
  const assistantMsg: Message = {
    id: generateId(),
    role: 'assistant',
    content: '',
    timestamp: new Date().toISOString(),
    streaming: true,
  }
  chatStore.addMessage(assistantMsg)
  chatStore.setStreaming(true)

  // Start SSE
  chatSSE(text, activeSessionId.value, {
    onMessage: (content: string) => {
      chatStore.updateLastMessage(content)
    },
    onDone: (threadId: string) => {
      chatStore.setStreaming(false)
      // Update last message in messages to remove streaming flag
      const msgs = chatStore.messages
      const last = msgs[msgs.length - 1]
      if (last) last.streaming = false

      // Create or update session
      activeSessionId.value = threadId
      const existing = chatStore.sessions.find(s => s.id === threadId)
      if (!existing) {
        chatStore.sessions.unshift({
          id: threadId,
          title: text.slice(0, 30) + (text.length > 30 ? '...' : ''),
          lastMessage: text.slice(0, 50),
          updatedAt: new Date().toISOString(),
          messageCount: chatStore.messages.length,
        })
      }
      chatStore.selectSession(threadId)
    },
    onError: (err: Error) => {
      chatStore.setStreaming(false)
      chatStore.updateLastMessage('抱歉，发生了错误: ' + err.message)
      const last = chatStore.messages[chatStore.messages.length - 1]
      if (last) last.streaming = false
    },
  })
}
</script>

<template>
  <div class="h-screen flex overflow-hidden bg-white">
    <SessionSidebar />
    <div class="flex-1 flex flex-col min-w-0">
      <ChatHeader />
      <MessageList />
      <ChatInput @send="handleSend" />
    </div>
  </div>
</template>
