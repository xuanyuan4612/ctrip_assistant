import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'
import { login as apiLogin, register as apiRegister } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<User | null>(JSON.parse(localStorage.getItem('user') || 'null'))
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value)

  async function loginAction(username: string, password: string) {
    loading.value = true
    try {
      const res = await apiLogin({ username, password })
      token.value = res.token
      user.value = { id: res.id, username: res.username, phone: res.phone, realName: res.realName }
      localStorage.setItem('token', res.token)
      localStorage.setItem('user', JSON.stringify(user.value))
      return true
    } finally { loading.value = false }
  }

  async function registerAction(username: string, password: string) {
    loading.value = true
    try {
      const res = await apiRegister({ username, password })
      token.value = res.token
      user.value = { id: res.id, username: res.username }
      localStorage.setItem('token', res.token)
      localStorage.setItem('user', JSON.stringify(user.value))
      return true
    } finally { loading.value = false }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { token, user, loading, isAuthenticated, loginAction, registerAction, logout }
})
