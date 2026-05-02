import type { LoginRequest, LoginResponse, ChatResponse } from '@/types'

const BASE = '/api/v1'

function authHeader(): Record<string, string> {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('登录失败')
  return res.json()
}

export async function register(data: LoginRequest): Promise<LoginResponse> {
  const res = await fetch(`${BASE}/auth/register`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('注册失败')
  return res.json()
}

export async function chat(userInput: string, threadId?: string): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/graph/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ user_input: userInput, thread_id: threadId || null, stream: false }),
  })
  if (!res.ok) throw new Error('对话失败')
  return res.json()
}

export function chatSSE(userInput: string, threadId: string | null, callbacks: {
  onMessage: (text: string) => void
  onDone: (threadId: string) => void
  onError: (err: Error) => void
}): AbortController {
  const controller = new AbortController()
  fetch(`${BASE}/graph/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ user_input: userInput, thread_id: threadId, stream: true }),
    signal: controller.signal,
  }).then(async res => {
    const reader = res.body?.getReader()
    if (!reader) return
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.content) callbacks.onMessage(data.content)
            if (data.thread_id) callbacks.onDone(data.thread_id)
          } catch {}
        }
      }
    }
  }).catch(err => callbacks.onError(err))
  return controller
}

export async function fetchUsers(): Promise<unknown[]> {
  const res = await fetch(`${BASE}/users`, { headers: authHeader() })
  return res.json()
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/health`)
    return res.ok
  } catch { return false }
}
