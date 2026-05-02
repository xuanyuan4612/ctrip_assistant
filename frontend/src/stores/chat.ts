import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Message, Session } from '@/types'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string | null>(null)
  const isStreaming = ref(false)
  const sidebarOpen = ref(true)

  const currentSession = computed(() => sessions.value.find(s => s.id === currentSessionId.value))

  function addMessage(msg: Message) { messages.value.push(msg) }
  function updateLastMessage(content: string) {
    const last = messages.value[messages.value.length - 1]
    if (last) last.content = content
  }

  function newSession() {
    currentSessionId.value = null
    messages.value = []
  }

  function selectSession(id: string) {
    currentSessionId.value = id
  }

  function toggleSidebar() { sidebarOpen.value = !sidebarOpen.value }

  function setStreaming(v: boolean) { isStreaming.value = v }

  return {
    messages, sessions, currentSessionId, isStreaming, sidebarOpen,
    currentSession, addMessage, updateLastMessage, newSession, selectSession, toggleSidebar, setStreaming,
  }
})
